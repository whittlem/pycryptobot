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
5. It's highly recommend to set `"disablecleanfilesonexit": 1`, in other case if pod gracefully restart you'll lose running crypto-bots


## Running Telegram bot with K8S operator
K8S Operator is build on top of [Operator SDK](https://sdk.operatorframework.io/docs/building-operators/helm/tutorial/)
It's required to have RWX(ReadWriteMany) Persistent Volume for correct working, telegram-bot is controlling pycryptobots with `telegram_data` folder so this folder should be shared across all pods 

1. Build and deploy operator
   1. if you plan to use your own image run ```make docker-build docker-push IMG=gcr.io/your-project/pycryptobot-operator:latest``` (it supports any docker registry)
   2. install operator, `make install deploy IMG=gcr.io/your-project/pycryptobot-operator:latest`
   3. check if CRD is created, run `kubectl get crd | grep pycryptobot`
   4. check if operator manager is running `kubectl get pod -A -l control-plane=controller-manager`
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