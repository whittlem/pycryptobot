# Build the manager binary
FROM quay.io/operator-framework/helm-operator:v1.15.0

ENV HOME=/opt/helm
COPY ./pycryptobot-operator/watches.yaml ${HOME}/watches.yaml
ADD ./chart  ${HOME}/helm-charts/pycryptobot
WORKDIR ${HOME}