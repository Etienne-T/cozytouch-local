-- MQTT 3.1.1 subset: clean session, retained QoS1, LWT, keepalive.
-- No subscribe, incoming commands, TLS, credentials, or production endpoints.
local M={}
local function u16(n) assert(n>=0 and n<65536 and n%1==0);return string.char(math.floor(n/256),n%256) end
local function str(s) assert(type(s)=='string' and #s<=65535);return u16(#s)..s end
local function remaining(n)
  assert(n>=0 and n<=4096);local bytes={}
  repeat local b=n%128;n=math.floor(n/128);if n>0 then b=b+128 end;bytes[#bytes+1]=string.char(b) until n==0
  return table.concat(bytes)
end
function M.packet(header,payload) return string.char(header)..remaining(#payload)..payload end
function M.connect_packet(c)
  return M.packet(0x10,str('MQTT')..string.char(4,0x2e)..u16(20)..str(c.client_id)..str(c.topic_prefix..'/availability')..str('offline'))
end
function M.publish_packet(topic,payload,id,retain)
  assert(#topic<=200 and #payload<=2048 and id>=1 and id<=65535,'outgoing MQTT bounds')
  return M.packet(retain and 0x33 or 0x32,str(topic)..u16(id)..payload)
end
function M.parser()
  local p={buf=''}
  function p:feed(data)
    assert(#data<=4096 and #self.buf+#data<=8192,'MQTT receive bound');self.buf=self.buf..data;local rows={}
    while #self.buf>=2 do
      local n,m,pos=0,1,2;local complete=false
      for _=1,4 do
        if pos>#self.buf then break end
        local b=self.buf:byte(pos);n=n+(b%128)*m;pos=pos+1
        assert(n<=64,'unexpected large MQTT server packet')
        if b<128 then complete=true;break end;m=m*128
        assert(pos<=5,'malformed MQTT remaining length')
      end
      if not complete or #self.buf<pos+n-1 then break end
      rows[#rows+1]={header=self.buf:byte(1),data=self.buf:sub(pos,pos+n-1)};self.buf=self.buf:sub(pos+n)
    end
    return rows
  end
  return p
end
function M.new(config,transport,log)
  local c={config=config,io=transport,log=log or function() end,state='disconnected',next_try=0,backoff=1,latest={},dirty={},acknowledged={},pid=0,tx='',parser=M.parser(),inflight=nil,acks=0,connections=0,availability='starting',ping_at=nil,last_io=0,last_tx=0}
  function c:set(topic,payload,retain)
    assert(topic:sub(1,#config.topic_prefix+1)==config.topic_prefix..'/' and #topic<=200 and #payload<=2048,'MQTT publication allowlist/bound')
    assert(topic==config.topic_prefix..'/availability' or topic==config.topic_prefix..'/cethi/state' or topic==config.topic_prefix..'/ic3/state' or topic==config.topic_prefix..'/test/state','MQTT topic not allowed')
    self.latest[topic]={payload=payload,retain=retain~=false};self.dirty[topic]=true
    local count=0;for _ in pairs(self.latest) do count=count+1 end;assert(count<=4,'publication queue bound')
  end
  function c:set_availability(value)
    assert(value=='starting' or value=='online' or value=='offline','availability value')
    self.availability=value;self:set(config.topic_prefix..'/availability',value,true)
  end
  function c:disconnect(now,reason)
    self.io:close();self.state='disconnected';self.tx='';self.inflight=nil;self.parser=M.parser();self.ping_at=nil
    for topic in pairs(self.latest) do self.dirty[topic]=true end
    self.next_try=now+self.backoff;self.backoff=math.min(self.backoff*2,16)
    self.log('MQTT_DISCONNECTED reason='..tostring(reason)..' retry_seconds='..(self.next_try-now))
  end
  function c:close_abrupt()
    self.io:close();self.state='closed';self.tx='';self.inflight=nil
  end
  function c:queue(packet,now) assert(#self.tx+#packet<=4096,'MQTT send bound');self.tx=self.tx..packet end
  function c:step(now)
    if self.state=='closed' then return end
    local ok,err=pcall(function()
      if self.state=='disconnected' then
        if now<self.next_try then return end
        self.io:open();self.state='connecting';self.deadline=now+3;self.log('MQTT_CONNECTING')
      end
      if self.state=='connecting' then
        assert(now<self.deadline,'connect timeout')
        if not self.io:connected() then return end
        self.state='connack';self.deadline=now+3;self:queue(M.connect_packet(config),now);self.last_io=now;self.last_tx=now
      end
      if #self.tx>0 then
        local n=self.io:write(self.tx)
        assert(n>=0 and n<=#self.tx,'invalid socket write count')
        if n>0 then self.tx=self.tx:sub(n+1);self.last_io=now;self.last_tx=now end
      end
      local data=self.io:read()
      if data and #data>0 then
        self.last_io=now
        for _,p in ipairs(self.parser:feed(data)) do
          if self.state=='connack' then
            assert(p.header==0x20 and #p.data==2 and p.data:byte(1)==0 and p.data:byte(2)==0,'CONNACK refused or invalid')
            self.state='ready';self.connections=self.connections+1
            -- Backoff resets only after a successful QoS1 acknowledgement,
            -- so an endpoint that repeatedly disconnects cannot cause spin.
            for topic in pairs(self.latest) do self.dirty[topic]=true end
            self:set_availability(self.availability);self.log('MQTT_CONNECTED clean_session=true')
          elseif self.state=='ready' then
            if p.header==0x40 then
              assert(#p.data==2 and self.inflight,'unexpected PUBACK')
              local id=p.data:byte(1)*256+p.data:byte(2);assert(id==self.inflight.id,'uncorrelated PUBACK')
              local sent=self.inflight;self.inflight=nil;self.acks=self.acks+1;self.backoff=1
              self.acknowledged[sent.topic]=sent.payload
              -- A newer value can replace a topic while its older packet is
              -- in flight. Clear dirty only when the acknowledged payload is
              -- still the latest value.
              if self.latest[sent.topic] and self.latest[sent.topic].payload==sent.payload then self.dirty[sent.topic]=nil end
              self.log('MQTT_PUBACK topic_suffix='..sent.topic:sub(#config.topic_prefix+2)..' ack_count='..self.acks)
            elseif p.header==0xd0 then assert(#p.data==0 and self.ping_at,'unexpected PINGRESP');self.ping_at=nil
            else error('unexpected MQTT packet; no incoming commands supported') end
          else error('MQTT packet in invalid state') end
        end
      end
      if self.state=='connack' then assert(now<self.deadline,'CONNACK timeout') end
      if self.state=='ready' then
        if self.inflight then assert(now<self.inflight.deadline,'PUBACK timeout') end
        if self.ping_at then assert(now-self.ping_at<5,'PINGRESP timeout') end
        if not self.inflight and #self.tx==0 then
          local topic=nil;local availability=config.topic_prefix..'/availability'
          if self.dirty[availability] then topic=availability else for _,suffix in ipairs({'cethi/state','ic3/state','test/state'}) do local candidate=config.topic_prefix..'/'..suffix;if self.dirty[candidate] then topic=candidate;break end end end
          if topic then
            local value=self.latest[topic];self.pid=self.pid%65535+1
            self.inflight={id=self.pid,topic=topic,payload=value.payload,deadline=now+5}
            self:queue(M.publish_packet(topic,value.payload,self.pid,value.retain),now)
          end
        end
        if now-self.last_tx>=8 and not self.ping_at and #self.tx==0 then self:queue(string.char(0xc0,0),now);self.ping_at=now end
      end
    end)
    if not ok then self:disconnect(now,'protocol_or_transport_error');self.last_error=tostring(err) end
  end
  function c:offline_acked() return self.state=='ready' and self.latest[config.topic_prefix..'/availability'] and self.latest[config.topic_prefix..'/availability'].payload=='offline' and not self.dirty[config.topic_prefix..'/availability'] and not self.inflight and #self.tx==0 end
  function c:graceful_disconnect()
    assert(self:offline_acked(),'offline publication not acknowledged')
    -- A short/nonblocking DISCONNECT write is insufficient: close without a
    -- complete packet causes the broker to publish the already-offline LWT.
    pcall(function() self.io:write(string.char(0xe0,0)) end);self:close_abrupt()
  end
  return c
end
return M
