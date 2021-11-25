## Running Telegram bot in K8S
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
5. It's highly recommend to set `"disablecleanfilesonexit": 1`(in config.json -> marker(binance|coinbasepro) section), in other case if pod gracefully restart you'll lose running crypto-bots

### Example values file:
```yaml
config: >
  {
    "binance": {
      "api_url": "https://api.binance.com",
      "config": {
        ...
        "enabletelegrambotcontrol": 1,
        "disablecleanfilesonexit": 1
      },
      "api_key_file": "/app/keys/binance.key"
    },
    "telegram": {
      "token": "...",
      "client_id": "...",
      "user_id": "..."
    },
    "scanner": {
      "atr72_pcnt" : 3.0,
      "enableexitaftersell" : 1,
      "enableleverage" : 0,
      "maxbotcount" : 10,
      "autoscandelay" : 1,
      "enable_buy_next": 1
    }
  }
scanner: >
  {
      "binance" : {
          "quote_currency": ["USDT"]
      }
  }
binance_key: |
  XXXXXXXXxXXXXXXXXXXXXXX
  YYYYYYYYYYYYYYYYYYYYYYY
  
telegramBot:
  persistence:
    enabled: true
    storageClass: some-storage-class
    accessMode: ReadWriteMany|ReadWriteOnce
command:
  - python3
  - -u
  - telegram_bot.py
  - --restart-on-init

resources: #For approx 20 bots
 requests:
   cpu: 500m
   memory: 1Gi
 limits:
   cpu: 2
   memory: 3.5Gi
```



## Running Telegram bot with K8S operator
K8S Operator is build on top of [Operator SDK](https://sdk.operatorframework.io/docs/building-operators/helm/tutorial/)
It's required to have RWX(ReadWriteMany) Persistent Volume for correct working, telegram-bot is controlling pycryptobots with `telegram_data` folder so this folder should be shared across all pods 

1. Build and deploy operator
   1. go to `pycryptobot-operator` folder, `cd pycryptobot-operator`
   2. if you plan to use your own image run ```make docker-build docker-push IMG=gcr.io/your-project/pycryptobot-operator:latest``` (it supports any docker registry)
   3. install operator, `make install deploy IMG=gcr.io/your-project/pycryptobot-operator:latest`
   4. check if CRD is created, run `kubectl get crd | grep pycryptobot`
   5. check if operator manager is running `kubectl get pod -A -l control-plane=controller-manager`
2. Deploy Telegram bot as described above with few changes:
   1. Change command to:
   ```yaml 
      command:
        - python3
        - -u
        - telegram_bot.py
        - --restart-on-init
        - --use-k8s-operator 
      ```
    2. You can use smaller `resources.requests` and `resources.limits`
    3. add to values to telegram-bot deployment
    ```yaml
    operatorDefaults:
      metadata:
        namespace: cryptobot
      spec:
        telegramBot:
          persistence:
            enabled: true
            existingClaimName: task-pv-claim #Should be the same PVC that TG bod is using
        existingConfig: telegrambot-test-pycryptobot #Recomended be the same configmap that TG bod is using
        existingSecret: telegrambot-test-pycryptobot #Recomended be the same secret that TG bod is using
    useK8SOperator: true
    ```
   
### Example values file:
```yaml
config: >
  {
    "binance": {
      "api_url": "https://api.binance.com",
      "config": {
        ...
        "enabletelegrambotcontrol": 1,
        "disablecleanfilesonexit": 1
      },
      "api_key_file": "/app/keys/binance.key"
    },
    "telegram": {
      "token": "...",
      "client_id": "...",
      "user_id": "..."
    },
    "scanner": {
      "atr72_pcnt" : 3.0,
      "enableexitaftersell" : 1,
      "enableleverage" : 0,
      "maxbotcount" : 10,
      "autoscandelay" : 1,
      "enable_buy_next": 1
    }
  }
scanner: >
  {
      "binance" : {
          "quote_currency": ["USDT"]
      }
  }
binance_key: |
  XXXXXXXXxXXXXXXXXXXXXXX
  YYYYYYYYYYYYYYYYYYYYYYY
  
telegramBot:
  persistence:
    enabled: true
    storageClass: some-storage-class
    accessMode: ReadWriteMany # important to use RWX
command:
  - python3
  - -u
  - telegram_bot.py
  - --restart-on-init
  - --use-k8s-operator


resources:
 requests:
   cpu: 50m
   memory: 100Mi
   
operatorDefaults:
  metadata:
    namespace: cryptobot
  spec:
    telegramBot:
      persistence:
        enabled: true
        existingClaimName: telegrambot-pycryptobot-telegram-data
    existingConfig: telegrambot-pycryptobot
    existingSecret: telegrambot-pycryptobot
    image: #Optionaly you can use your own image
      repository: gcr.io/<repository>/pycryptobot
    resources:
      requests:
        cpu: 50m
        memory: 100Mi
useK8SOperator: true
```