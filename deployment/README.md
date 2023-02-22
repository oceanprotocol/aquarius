<!--
Copyright 2023 Ocean Protocol Foundation
SPDX-License-Identifier: Apache-2.0
-->
- [Kubernetes deployment](#kubernetes-deployment)
  * [Elasticsearch](#elasticsearch)
  * [Aquarius](#aquarius)
- [Docker Compose deployment](#docker-compose-deployment)
  * [Single systemd service (Aquarius+Elasticsearch)](#single-systemd-service-aquariuselasticsearch)
  * [Separate systemd services for Aquarius and Elasticsearch](#separate-systemd-services-for-aquarius-and-elasticsearch)






#### Kubernetes deployment

[Aquarius](https://github.com/oceanprotocol/aquarius) depends on the backend database and in this example we will deploy the following resources:

- Elasticsearch  (as [StatefulSet](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/))  - database backend.

- Aquarius ([Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/))


Templates (yaml files) are provided and could be customized based on the environment's specifics.



##### Elasticsearch

More customization parameters could be offered through Helm [chart deployment](https://github.com/elastic/helm-charts/tree/master/elasticsearch).
Additional things to consider on a production deployment - number of replicas, memory heap size, etc. Check the [guide](https://www.elastic.co/guide/en/cloud-on-k8s/current/index.html) for recommended practices.

[elasticsearch-master-sts.yaml](./elasticsearch-master-sts.yaml)

After the above file is customized, the following example shows how it can be deployed:

```
$ kubectl create ns ocean
$ kubectl config set-context --current --namespace ocean
$ kubectl apply -f elasticsearch-master-sts.yaml


$ kubectl get pods,svc
NAME                         READY   STATUS    RESTARTS   AGE
pod/elasticsearch-master-0   1/1     Running   0          8h
pod/elasticsearch-master-1   1/1     Running   0          8h
pod/elasticsearch-master-2   1/1     Running   0          8h


NAME                                    TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)             AGE
service/elasticsearch-master            ClusterIP   172.20.70.12   <none>        9200/TCP,9300/TCP   8h
service/elasticsearch-master-headless   ClusterIP   None           <none>        9200/TCP,9300/TCP   8h
```

Once the Elasticsearch pods are running, the database service should be available:

```
$ kubectl port-forward --namespace ocean svc/elasticsearch-master 9200:9200
Forwarding from 127.0.0.1:9200 -> 9200
Forwarding from [::1]:9200 -> 9200
```

```
$ curl localhost:9200
Handling connection for 9200
{
  "name" : "elasticsearch-master-1",
  "cluster_name" : "elasticsearch",
  "cluster_uuid" : "izZH8nHGReq-TxrD-NrSOA",
  "version" : {
    "number" : "6.8.15",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "c9a8c60",
    "build_date" : "2021-03-18T06:33:32.588487Z",
    "build_snapshot" : false,
    "lucene_version" : "7.7.3",
    "minimum_wire_compatibility_version" : "5.6.0",
    "minimum_index_compatibility_version" : "5.0.0"
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
- rinkeby
- ropsten

and the following templates (annotated) could be edited and used for deployment.

*[aquarius-deployment.yaml](./aquarius-deployment.yaml)* (annotated) => this deployment is responsible for serving API requests

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
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
        - name: AQUARIUS_BIND_URL
          value: http://0.0.0.0:5000
        - name: AQUARIUS_WORKERS
          value: "8"
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
          value: elastic
        - name: DB_PASSWORD
          value: changeme
        - name: RUN_AQUARIUS_SERVER
          value: "1"
        - name: RUN_EVENTS_MONITOR
          value: "0"
        - name: EVENTS_ALLOW
          value: "0"
        - name: ALLOWED_PUBLISHERS
          value: '[""]'
        image: oceanprotocol/aquarius:v3.0.1 => check the available versions: https://hub.docker.com/repository/docker/oceanprotocol/aquarius
        imagePullPolicy: IfNotPresent
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
            cpu: 500m
            memory: 500Mi
          requests:
            cpu: 500m
            memory: 500Mi
        terminationMessagePath: /dev/termination-log
        terminationMessagePolicy: File
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      schedulerName: default-scheduler
      terminationGracePeriodSeconds: 30
```



Example deployment for *Rinkeby* (Ethereum testenet):

[aquarius-events-rinkeby-deployment.yaml](./aquarius-events-rinkeby-deployment.yaml) (annotated) => this deployment will be responsabile for indexing the block and storing the metadata published on-chain:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: aquarius-events-rinkeby
  name: aquarius-events-rinkeby
spec:
  progressDeadlineSeconds: 600
  replicas: 1
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: aquarius-events-rinkeby
  strategy:
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
    type: RollingUpdate
  template:
    metadata:
      creationTimestamp: null
      labels:
        app: aquarius-events-rinkeby
    spec:
      containers:
      - env:
        - name: LOG_LEVEL
          value: DEBUG
        - name: AQUARIUS_BIND_URL
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
          value: elastic
        - name: DB_PASSWORD
          value: changeme
        - name: RUN_AQUARIUS_SERVER
          value: "0"
        - name: RUN_EVENTS_MONITOR
          value: "1"
        - name: ALLOWED_PUBLISHERS
          value: '[""]'
        - name: BFACTORY_BLOCK
          value: "7298806"
        - name: METADATA_CONTRACT_BLOCK
          value: "7298808"
        - name: NETWORK_NAME
          value: rinkeby
        - name: EVENTS_RPC
          value: < RPC service for Rinkeby >
        - name: OCEAN_ADDRESS
          value: 0x8967BCF84170c91B0d24D4302C2376283b0B3a07
        - name: BLOCKS_CHUNK_SIZE
          value: "5000"
        - name: EVENTS_HTTP
          value: "1"
        image: oceanprotocol/aquarius:v3.0.1 => check the available versions: https://hub.docker.com/repository/docker/oceanprotocol/aquarius
        imagePullPolicy: IfNotPresent
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
        name: aquarius-events-rinkeby
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
            memory: 500Mi
          requests:
            cpu: 500m
            memory: 500Mi
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


$ kubectl get pods -l app=aquarius
NAME                        READY   STATUS    RESTARTS   AGE
aquarius-5b59cd887b-87z5c   1/1     Running   0          2d10h

$ kubectl get pods -l app=aquarius-events-rinkeby
NAME                                       READY   STATUS    RESTARTS   AGE
aquarius-events-rinkeby-55747d89f7-9f69q   1/1     Running   0          2d7h
```



check the logs for newly deployed Aquarius:

```shell
$ kubectl logs aquarius-5b59cd887b-87z5c [--follow]

$ kubectl logs aquarius-events-rinkeby-55747d89f7-9f69q [--follow]
```


next step is to create a [service](https://kubernetes.io/docs/concepts/services-networking/service/) (eg. ClusterIP,  NodePort,  Loadbalancer, ExternalName) for this deployment depending on environment specs.




#### Docker Compose deployment



##### Single systemd service (Aquarius+Elasticsearch)

a) create */etc/docker/compose/aquarius/docker-compose.yml* file

 */etc/docker/compose/aquarius/docker-compose.yml* (annotated - this example use rinkeby network)

```yaml
version: '3'
services:
  elasticsearch:
    image: elasticsearch:6.8.17
    container_name: elasticsearch
    restart: on-failure
    environment:
      ES_JAVA_OPTS: "-Xms512m -Xmx512m"
      MAX_MAP_COUNT: "64000"
      discovery.type: "single-node"
    volumes:
      - data:/usr/share/elasticsearch/data
    ports:
      - 9200:9200
    networks:
      - ocean_backend
  aquarius:
    image: oceanprotocol/aquarius:v3.0.1 => check the available versions: https://hub.docker.com/repository/docker/oceanprotocol/aquarius
    container_name: aquarius
    restart: on-failure
    ports:
      - 5000:5000
    networks:
      - ocean_backend
    depends_on:
      - elasticsearch
    environment:
      DB_MODULE: elasticsearch
      DB_HOSTNAME: elasticsearch
      DB_PORT: 9200
      DB_USERNAME: elastic
      DB_PASSWORD: changeme
      DB_NAME: aquarius
      DB_SCHEME: http
      LOG_LEVEL: "DEBUG"
      AQUARIUS_BIND_URL : "http://0.0.0.0:5000"
      AQUARIUS_WORKERS : "8"
      RUN_AQUARIUS_SERVER: "1"
      EVENTS_ALLOW: 0
      RUN_EVENTS_MONITOR: 0
      ALLOWED_PUBLISHERS: '[""]'
  aquarius-events-rinkeby:
    image: oceanprotocol/aquarius:v3.0.1 => check the available versions: https://hub.docker.com/repository/docker/oceanprotocol/aquarius
    container_name: aquarius-events-rinkeby
    restart: on-failure
    networks:
      - ocean_backend
    depends_on:
      - elasticsearch
    environment:
      DB_MODULE: elasticsearch
      DB_HOSTNAME: elasticsearch
      DB_PORT: 9200
      DB_USERNAME: elastic
      DB_PASSWORD: changeme
      DB_NAME: aquarius
      DB_SCHEME: http
      LOG_LEVEL: "DEBUG"
      AQUARIUS_BIND_URL: "http://0.0.0.0:5000"
      AQUARIUS_WORKERS : "1"
      RUN_AQUARIUS_SERVER : "0"
      NETWORK_NAME: "rinkeby"
      EVENTS_RPC: "https://rinkeby.infura.io/v3/<your Infura id project>"
      BFACTORY_BLOCK: 7298806
      METADATA_CONTRACT_BLOCK: 7298808
      METADATA_UPDATE_ALL : "0"
      OCEAN_ADDRESS :  0x8967BCF84170c91B0d24D4302C2376283b0B3a07
      EVENTS_ALLOW: 0
      RUN_EVENTS_MONITOR: 1
      BLOCKS_CHUNK_SIZE: "5000"
volumes:
  data:
    driver: local
networks:
  ocean_backend:
    driver: bridge
```



b) create */etc/systemd/system/docker-compose@aquarius.service* file

```
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
  "name" : "bMXlD3J",
  "cluster_name" : "docker-cluster",
  "cluster_uuid" : "1EkfoURDTai19VywHSJBgw",
  "version" : {
    "number" : "6.8.17",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "206f6a2",
    "build_date" : "2021-07-01T18:51:20.391869Z",
    "build_snapshot" : false,
    "lucene_version" : "7.7.3",
    "minimum_wire_compatibility_version" : "5.6.0",
    "minimum_index_compatibility_version" : "5.0.0"
  },
  "tagline" : "You Know, for Search"
}

```



```shell
$ curl localhost:5000
{"plugin":"elasticsearch","software":"Aquarius","version":"3.0.1"}
```



use docker cli to check aquarius service logs:

== identify container id

```shell
$ docker ps
CONTAINER ID   IMAGE                           COMMAND                  CREATED          STATUS          PORTS                              NAMES
cb43417b4fcc   oceanprotocol/aquarius:v3.0.1   "/aquarius/docker-en…"   32 seconds ago   Up 31 seconds   0.0.0.0:5000->5000/tcp             aquarius
734a3b2db62a   oceanprotocol/aquarius:v3.0.1   "/aquarius/docker-en…"   32 seconds ago   Up 31 seconds   5000/tcp                           aquarius-events-rinkeby
b33f8f3f144b   elasticsearch:6.8.17            "/usr/local/bin/dock…"   34 seconds ago   Up 32 seconds   0.0.0.0:9200->9200/tcp, 9300/tcp   elasticsearch

```



== check logs from aquarius docker containers

```shell
$ docker logs cb43417b4fcc [--follow]
$ docker logs 734a3b2db62a [--follow]

```



##### Separate systemd services for Aquarius and Elasticsearch

While this setup might be flexible as services are managed individually, there is a dependency between docker containers imposed by [network communication](https://docs.docker.com/compose/networking/) constraints.

The following steps could be used as example:

a) create */etc/docker/compose/elasticsearch/docker-compose.yml* file

*/etc/docker/compose/elasticsearch/docker-compose.yml*

```yaml
version: '3'
services:
  elasticsearch:
    image: elasticsearch:6.8.17
    container_name: elasticsearch
    restart: on-failure
    environment:
      ES_JAVA_OPTS: "-Xms512m -Xmx512m"
      MAX_MAP_COUNT: "262144"
      discovery.type: "single-node"
    volumes:
      - data:/usr/share/elasticsearch/data
    ports:
      - 9200:9200
    networks:
      - backend

volumes:
  data:
    driver: local
networks:
  backend:
    driver: bridge
```



b) create /etc/docker/compose/aquarius/docker-compose.yml file (this example is using **ropsten** network).

Check [Ocean Contracts](https://github.com/oceanprotocol/contracts#-network-deployments) for deployment on common Ethereum networks.

*/etc/docker/compose/aquarius/docker-compose.yml*  (annotated)

```yaml
    version: '3'
services:
  aquarius:
    image: oceanprotocol/aquarius:v3.0.1 => check the available versions: https://hub.docker.com/repository/docker/oceanprotocol/aquarius
    container_name: aquarius
    restart: on-failure
    ports:
      - 5000:5000
    networks:
      - ocean_backend
    environment:
      DB_MODULE: elasticsearch
      DB_HOSTNAME: elasticsearch
      DB_PORT: 9200
      DB_USERNAME: elastic
      DB_PASSWORD: changeme
      DB_NAME: aquarius
      DB_SCHEME: http
      LOG_LEVEL: "DEBUG"
      AQUARIUS_BIND_URL : "http://0.0.0.0:5000"
      AQUARIUS_WORKERS : "8"
      RUN_AQUARIUS_SERVER: "1"
      EVENTS_ALLOW: 0
      RUN_EVENTS_MONITOR: 0
      ALLOWED_PUBLISHERS: '[""]'
  aquarius-events-rinkeby:
    image: oceanprotocol/aquarius:v3.0.1 => check the available versions: https://hub.docker.com/repository/docker/oceanprotocol/aquarius
    container_name: aquarius-events-rinkeby
    restart: on-failure
    networks:
      - ocean_backend
    environment:
      DB_MODULE: elasticsearch
      DB_HOSTNAME: elasticsearch
      DB_PORT: 9200
      DB_USERNAME: elastic
      DB_PASSWORD: changeme
      DB_NAME: aquarius
      DB_SCHEME: http
      LOG_LEVEL: "DEBUG"
      AQUARIUS_BIND_URL: "http://0.0.0.0:5000"
      AQUARIUS_WORKERS : "1"
      RUN_AQUARIUS_SERVER : "0"
      ALLOWED_PUBLISHERS: '[""]'
      NETWORK_NAME: "rinkeby"
      EVENTS_RPC: "https://rinkeby.infura.io/v3/< your Infura project id >"
      BFACTORY_BLOCK: 7298806
      METADATA_CONTRACT_BLOCK: 7298808
      METADATA_UPDATE_ALL : "0"
      OCEAN_ADDRESS :  0x8967BCF84170c91B0d24D4302C2376283b0B3a07
      EVENTS_ALLOW: 0
      RUN_EVENTS_MONITOR: 1
      BLOCKS_CHUNK_SIZE: "50000"
networks:
  ocean_backend:
    external: true
```


c) create /etc/systemd/system/docker-compose@elasticsearch.service file

*/etc/systemd/system/docker-compose@elasticsearch.service*

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


[Install]
WantedBy=multi-user.target
```



d) create */etc/systemd/system/docker-compose@aquarius.service* file (make sure Aquarius service will start after Elasticsearch if enabled at boot)

 */etc/systemd/system/docker-compose@aquarius.service*

```shell
[Unit]
Description=%i service with docker compose
Requires=docker.service
After=docker.service docker-compose@elasticsearch.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=/etc/docker/compose/%i
ExecStartPre=/usr/bin/env docker-compose pull
ExecStart=/usr/bin/env docker-compose up -d --remove-orphans
ExecStop=/usr/bin/env docker-compose  stop
ExecStopPost=/usr/bin/env docker-compose down

[Install]
WantedBy=multi-user.target
```



e) run:

```shell
$ sudo systemctl daemon-reload
```

optional - enable services to start at boot:

```shell
$ sudo systemctl enable docker-compose@elasticsearch.service
$ sudo systemctl enable docker-compose@aquarius.service
```



f) start Elasticsearch service:

```
$ sudo systemctl start docker-compose@elasticsearch.service
```

check status:

```shell
$ sudo systemctl status docker-compose@elasticsearch.service

```



confirm Elasticsearch service is accessible on localhost port 9200/tcp

```shell
$ curl localhost:9200

```



g) start Aquarius service:

```
$ sudo systemctl start docker-compose@aquarius.service
```



check the status:

```shell
$ sudo systemctl status docker-compose@aquarius.service

```



use docker cli to check aquarius service logs:

== identify container id

```shell
$ docker ps
CONTAINER ID   IMAGE                           COMMAND                  CREATED          STATUS         PORTS                              NAMES
30173843c1fc   elasticsearch:6.8.17            "/usr/local/bin/dock…"   3 minutes ago    Up 3 minutes   0.0.0.0:9200->9200/tcp, 9300/tcp   elasticsearch
f51c7e621c31   oceanprotocol/aquarius:v3.0.1   "/aquarius/docker-en…"   2 minutes ago    Up 2 minutes   0.0.0.0:5000->5000/tcp             aquarius
a83a031254ea   oceanprotocol/aquarius:v3.0.1   "/aquarius/docker-en…"   2 minutes ago    Up 2 minutes   5000/tcp                           aquarius-events-rinkeby

```



== check logs from aquarius docker containers

```shell
$ docker logs f51c7e621c31 [--follow]
$ docker logs a83a031254ea [--follow]
```


confirm Aquarius service is accessible on localhost port 5000/tcp

```shell
$ curl localhost:5000
{"plugin":"elasticsearch","software":"Aquarius","version":"3.0.1"}
```

