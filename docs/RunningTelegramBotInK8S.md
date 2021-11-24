## Running Telegram in K8S
1. Configure chart as usual
2. configure persistence, eg:
```yaml
telegramBot:
  persistence:
    enabled: true
    storageClass: somestorageclass
```
3. configure command:
```yaml
command:
  - python3
  - -u
  - telegram_bot.py
  - --restart-on-init
```
Note: `--restart-on-init` is highly recommended to add because in other case some pairs will not have pycryptobots to run after pod restart   
4. make sure you're allowing enough resources, eg:
```yaml
resources:
 requests:
   cpu: 500m
   memory: 1Gi
 limits:
   cpu: 2
   memory: 2.5Gi
```
5. It's highly recommend to set `"disablecleanfilesonexit": 1`, in other case if pod gracefully restart you'll lose running crypto-bots