<!--
Copyright 2023 Ocean Protocol Foundation
SPDX-License-Identifier: Apache-2.0
-->

- [Kubernetes deployment](#kubernetes-deployment)
  * [Elasticsearch](#elasticsearch)
  * [Aquarius](#aquarius)
  
- [Docker Compose deployment](#docker-compose-deployment)
  * [Single systemd service (Aquarius+Elasticsearch)](#single-systemd-service-aquariuselasticsearch)
  
    






#### Kubernetes deployment

[Aquarius](https://github.com/oceanprotocol/aquarius) depends on the backend database and in this example we will deploy the following resources:

- Elasticsearch.

- Aquarius ([Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/))


Templates (yaml files) are provided and could be customized based on the environment's specifics.



##### Elasticsearch

It is recommended to deploy Elasticsearch through Helm [chart](https://github.com/elastic/cloud-on-k8s).

Once the Elasticsearch pods are running, the database service should be available:

```shell
$ kubectl port-forward --namespace ocean svc/elasticsearch-master 9200:9200
Forwarding from 127.0.0.1:9200 -> 9200
Forwarding from [::1]:9200 -> 9200
```

```shell
$ curl localhost:9200
{
  "name" : "elasticsearch-master-2",
  "cluster_name" : "elasticsearch",
  "cluster_uuid" : "KMAfL5tVSJWFfmCOklT0qg",
  "version" : {
    "number" : "8.5.2",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "a846182fa16b4ebfcc89aa3c11a11fd5adf3de04",
    "build_date" : "2022-11-17T18:56:17.538630285Z",
    "build_snapshot" : false,
    "lucene_version" : "9.4.1",
    "minimum_wire_compatibility_version" : "7.17.0",
    "minimum_index_compatibility_version" : "7.0.0"
  },
  "tagline" : "You Know, for Search"
}
```

##### Aquarius



Aquarius supports indexing multiple chains using a single instance to serve API requests and one instance for each chain that must be indexed.


![image](https://user-images.githubusercontent.com/54084524/128821016-f2f2b98d-a62d-469a-9bca-dfd2164df3ae.png)



The following deployment templates could be used for guidance.
Some parameters are [optional](https://github.com/oceanprotocol/aquarius) and the template could be adjusted based on these considerations.
Common cases are the deployments for one/multiple multiple Ethereum networks:

- mainnet
- goerli
- mumbai

and the following templates (annotated) could be edited and used for deployment.

*[aquarius-deployment.yaml](./aquarius-deployment.yaml)* (annotated) => this deployment is responsible for serving API requests

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
  labels:
    app: aquarius
  name: aquarius
spec:
  progressDeadlineSeconds: 600
  replicas: 1
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: aquarius
  strategy:
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
    type: RollingUpdate
  template:
    metadata:
      creationTimestamp: null
      labels:
        app: aquarius
    spec:
      containers:
      - env:
        - name: LOG_LEVEL
          value: DEBUG
        - name: AQUARIUS_URL
          value: http://0.0.0.0:5000
        - name: AQUARIUS_WORKERS
          value: "4"
        - name: DB_HOSTNAME
          value: < ES service hostname >
        - name: DB_MODULE
          value: elasticsearch
        - name: DB_NAME
          value: aquarius
        - name: DB_PORT
          value: "9200"
        - name: DB_SCHEME
          value: http
        - name: DB_USERNAME
          value: < ES username >
        - name: DB_PASSWORD
          value: < ES password >
        - name: DB_SSL
          value: "false"
        - name: RUN_AQUARIUS_SERVER
          value: "1"
        - name: RUN_EVENTS_MONITOR
          value: "0"
        - name: EVENTS_ALLOW
          value: "0"
        - name: CONFIG_FILE
          value: config.ini
        - name: ALLOWED_PUBLISHERS
          value: '[""]'
        image: oceanprotocol/aquarius:v5.1.2 => check the available versions: https://hub.docker.com/repository/docker/oceanprotocol/aquarius/tags?page=1&ordering=last_updated
        imagePullPolicy: Always
        livenessProbe:
          failureThreshold: 3
          httpGet:
            path: /
            port: 5000
            scheme: HTTP
          initialDelaySeconds: 20
          periodSeconds: 10
          successThreshold: 1
          timeoutSeconds: 2
        name: aquarius
        ports:
        - containerPort: 5000
          protocol: TCP
        readinessProbe:
          failureThreshold: 3
          httpGet:
            path: /
            port: 5000
            scheme: HTTP
          initialDelaySeconds: 20
          periodSeconds: 10
          successThreshold: 1
          timeoutSeconds: 1
        resources:
          limits:
            cpu: 800m
            memory: 1Gi
          requests:
            cpu: 800m
            memory: 1Gi
        terminationMessagePath: /dev/termination-log
        terminationMessagePolicy: File
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      schedulerName: default-scheduler
      terminationGracePeriodSeconds: 30
```



Example deployment for *Mumbai* (Polygon testenet):

[aquarius-events-rinkeby-deployment.yaml](./aquarius-events-rinkeby-deployment.yaml) (annotated) => this deployment will be responsabile for indexing the block and storing the metadata published on-chain:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
  labels:
    app: aquarius-events-mumbai
  name: aquarius-events-mumbai
spec:
  progressDeadlineSeconds: 600
  replicas: 1
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: aquarius-events-mumbai
  strategy:
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
    type: RollingUpdate
  template:
    metadata:
      creationTimestamp: null
      labels:
        app: aquarius-events-mumbai
    spec:
      containers:
      - env:
        - name: LOG_LEVEL
          value: DEBUG
        - name: AQUARIUS_URL
          value: http://0.0.0.0:5000
        - name: AQUARIUS_WORKERS
          value: "1"
        - name: DB_HOSTNAME
          value: < ES service hostname >
        - name: DB_MODULE
          value: elasticsearch
        - name: DB_NAME
          value: aquarius
        - name: DB_PORT
          value: "9200"
        - name: DB_SCHEME
          value: http
        - name: DB_USERNAME
          value: < ES username >
        - name: DB_PASSWORD
          value: < ES password >
        - name: DB_SSL
          value: "false"
        - name: RUN_AQUARIUS_SERVER
          value: "0"
        - name: RUN_EVENTS_MONITOR
          value: "1"
        - name: CONFIG_FILE
          value: config.ini
        - name: ALLOWED_PUBLISHERS
          value: '[""]'
        - name: NETWORK_NAME
          value: mumbai
        - name: EVENTS_RPC
          value: https://polygon-mumbai.infura.io/v3/< INFURA ID > => or another RPC service for this network
        - name: METADATA_UPDATE_ALL
          value: "0"
        - name: ASSET_PURGATORY_URL
          value: https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json
        - name: ACCOUNT_PURGATORY_URL
          value: https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-accounts.json
        - name: PURGATORY_UPDATE_INTERVAL
          value: "60"
        - name: OCEAN_ADDRESS
          value: 0xd8992Ed72C445c35Cb4A2be468568Ed1079357c8
        - name: SUBGRAPH_URLS
          value: |
            {"80001": "https://v4.subgraph.mumbai.oceanprotocol.com"} => or your own deployed Ocean Subgraph service for this network
        - name: BLOCKS_CHUNK_SIZE
          value: "3500"
        - name: EVENTS_HTTP
          value: "1"
        image: oceanprotocol/aquarius:v5.1.2 => check the available versions: https://hub.docker.com/repository/docker/oceanprotocol/aquarius/tags?page=1&ordering=last_updated
        imagePullPolicy: Always
        livenessProbe:
          failureThreshold: 3
          httpGet:
            path: /
            port: 5001
            scheme: HTTP
          initialDelaySeconds: 20
          periodSeconds: 10
          successThreshold: 1
          timeoutSeconds: 1
        name: aquarius-events-mumbai
        ports:
        - containerPort: 5000
          protocol: TCP
        readinessProbe:
          failureThreshold: 3
          httpGet:
            path: /
            port: 5001
            scheme: HTTP
          initialDelaySeconds: 20
          periodSeconds: 10
          successThreshold: 1
          timeoutSeconds: 1
        resources:
          limits:
            cpu: 500m
            memory: 1Gi
          requests:
            cpu: 500m
            memory: 1Gi
        terminationMessagePath: /dev/termination-log
        terminationMessagePolicy: File
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      schedulerName: default-scheduler
      terminationGracePeriodSeconds: 30
```





Tip: before deployment you can [validate](https://github.com/instrumenta/kubeval) the yaml file.

```shell
$ kubectl apply -f aquarius-deployment.yaml
$ kubectl apply -f aquarius-events-rinkeby-deployment.yaml


kubectl get pods -l app=aquarius
NAME                        READY   STATUS    RESTARTS   AGE
aquarius-6fd9cc975b-fxr4d   1/1     Running   0          1d

 kubectl get pods -l app=aquarius-events-mumbai
NAME                                     READY   STATUS    RESTARTS   AGE
aquarius-events-mumbai-8748976c4-mh24n   1/1     Running   0          1d
```



check the logs for newly deployed Aquarius:

```shell
$ kubectl logs aquarius-6fd9cc975b-fxr4d [--follow]

$ kubectl logs aquarius-events-mumbai-8748976c4-mh24n [--follow]
```


next step is to create a [service](https://kubernetes.io/docs/concepts/services-networking/service/) (eg. ClusterIP,  NodePort,  Loadbalancer, ExternalName) for this deployment depending on environment specs.




#### Docker Compose deployment



##### Single systemd service (Aquarius+Elasticsearch)

a) create */etc/docker/compose/aquarius/docker-compose.yml* file

 */etc/docker/compose/aquarius/docker-compose.yml* (annotated - example for  `goerli` network)

```yaml
version: '3.9'
services:
  elasticsearch:
    image: elasticsearch:8.7.0
    container_name: elasticsearch
    restart: on-failure
    environment:
      ES_JAVA_OPTS: "-Xms512m -Xmx512m"
      MAX_MAP_COUNT: "64000"
      discovery.type: "single-node"
      ELASTIC_PASSWORD: "changeme"
      xpack.security.enabled: "false"
      xpack.security.http.ssl.enabled: "false"
    volumes:
      - data:/usr/share/elasticsearch/data
    ports:
      - 9200:9200
    networks:
      - backend
  aquarius:
    image: oceanprotocol/aquarius:v5.1.2
    container_name: aquarius
    restart: on-failure
    ports:
      - 5000:5000
    networks:
      - backend
    depends_on:
      - elasticsearch
    environment:
      DB_MODULE: elasticsearch
      DB_HOSTNAME: http://elasticsearch
      DB_PORT: 9200
      DB_USERNAME: elastic
      DB_PASSWORD: changeme
      DB_NAME: aquarius
      DB_SCHEME: http
      DB_SSL : "false"
      LOG_LEVEL: "INFO"
      AQUARIUS_URL: "http://0.0.0.0:5000"
      AQUARIUS_WORKERS : "4"
      RUN_AQUARIUS_SERVER: "1"
      AQUARIUS_CONFIG_FILE: "config.ini"
      EVENTS_ALLOW: 0
      RUN_EVENTS_MONITOR: 0
      ALLOWED_PUBLISHERS: '[""]'
  aquarius-events-goerli:
    image: oceanprotocol/aquarius:v5.1.2
    container_name: aquarius-events-goerli
    restart: on-failure
    networks:
      - backend
    depends_on:
      - elasticsearch
    environment:
      DB_MODULE: elasticsearch
      DB_HOSTNAME: http://elasticsearch
      DB_PORT: 9200
      DB_USERNAME: elastic
      DB_PASSWORD: changeme
      DB_NAME: aquarius
      DB_SCHEME: http
      DB_SSL : "false"
      LOG_LEVEL: "INFO"
      AQUARIUS_URL: "http://0.0.0.0:5000"
      AQUARIUS_WORKERS : "1"
      RUN_AQUARIUS_SERVER : "0"
      AQUARIUS_CONFIG_FILE: "config.ini"
      ALLOWED_PUBLISHERS: '[""]'
      NETWORK_NAME: "goerli"
      EVENTS_RPC: "https://goerli.infura.io/v3/<infura_id>"
      METADATA_UPDATE_ALL : "0"
      OCEAN_ADDRESS :  0xcfdda22c9837ae76e0faa845354f33c62e03653a
      RUN_EVENTS_MONITOR: 1
      BLOCKS_CHUNK_SIZE: "5000"
      SUBGRAPH_URLS:  "5: https://v4.subgraph.goerli.oceanprotocol.com"
volumes:
  data:
    driver: local
networks:
  backend:
    driver: bridge
```



b) create */etc/systemd/system/docker-compose@aquarius.service* file

```shell
[Unit]
Description=%i service with docker compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
Environment="PROJECT=ocean"
WorkingDirectory=/etc/docker/compose/%i
ExecStartPre=/usr/bin/env docker-compose -p $PROJECT pull
ExecStart=/usr/bin/env docker-compose -p $PROJECT up -d --remove-orphans
ExecStop=/usr/bin/env docker-compose -p $PROJECT stop
ExecStopPost=/usr/bin/env docker-compose -p $PROJECT down


[Install]
WantedBy=multi-user.target
```



c) run:

```shell
$ sudo systemctl daemon-reload
```

optional - enable service to start at boot:

```shell
$ sudo systemctl enable docker-compose@aquarius.service
```



d) start aquarius service:

```shell
$ sudo systemctl start docker-compose@aquarius.service
```



check status:

```shell
$ sudo systemctl status docker-compose@aquarius.service

```


```shell
$ curl localhost:9200
{
  "name" : "a93d989293ac",
  "cluster_name" : "docker-cluster",
  "cluster_uuid" : "Bs16cyCwRCOIbmaBUEj5fA",
  "version" : {
    "number" : "8.7.0",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "09520b59b6bc1057340b55750186466ea715e30e",
    "build_date" : "2023-03-27T16:31:09.816451435Z",
    "build_snapshot" : false,
    "lucene_version" : "9.5.0",
    "minimum_wire_compatibility_version" : "7.17.0",
    "minimum_index_compatibility_version" : "7.0.0"
  },
  "tagline" : "You Know, for Search"
}
```



```shell
$ curl localhost:5000
{"plugin":"module","software":"Aquarius","version":"5.1.2"}
```



use docker cli to check aquarius service logs:

== identify container names

```shell
$ docker ps
CONTAINER ID   IMAGE                           COMMAND                  CREATED              STATUS              PORTS                                                 NAMES
355baee34d50   oceanprotocol/aquarius:v5.1.2   "/aquarius/docker-en…"   About a minute ago   Up About a minute   5000/tcp                                              aquarius-events-goerli
f1f97d6f146f   oceanprotocol/aquarius:v5.1.2   "/aquarius/docker-en…"   About a minute ago   Up About a minute   0.0.0.0:5000->5000/tcp, :::5000->5000/tcp             aquarius
a93d989293ac   elasticsearch:8.7.0             "/bin/tini -- /usr/l…"   About a minute ago   Up About a minute   0.0.0.0:9200->9200/tcp, :::9200->9200/tcp, 9300/tcp   elasticsearch

```



== check logs from aquarius docker containers

```shell
$ docker logs aquarius  [--follow]
$ docker logs aquarius-events-goerli [--follow]

```


