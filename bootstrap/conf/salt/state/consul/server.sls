/etc/opt/consul.d/server-config.json:
  file.managed:
    - source: salt://consul/config/server/server-config.json
    - user: root
    - group: root
    - mode: 644
    
/usr/lib/systemd/system/consul-server.service:
  file.managed:
    - source: salt://consul/config/bootstrap/consul-server.service
    - user: root
    - group: root
    - mode: 744
    
consul-server:
  service.running:
    - enable: True
    - watch:
      - file: /etc/opt/consul.d/*
{%- set servers = salt['mine.get']('roles:(consul-server|consul-bootstrap)', 'network.get_hostname', 'grain_pcre').values() %}
{%- set nodename = salt['grains.get']('nodename') %}
# Create a list of servers that can be used to join the cluster
{%- set join_server = [] %}
{%- for server in servers if server != nodename %}
{% do join_server.append(server) %}
{%- endfor %}
join-cluster:
  cmd.run:
    - name: consul join {{ join_server[0] }}
