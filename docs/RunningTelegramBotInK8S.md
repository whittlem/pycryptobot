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
```
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