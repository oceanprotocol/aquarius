<!--
Copyright 2021 Ocean Protocol Foundation
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

*elasticsearch-master-sts-example.yaml*

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  labels:
    app: elasticsearch-master
    release: elasticsearch
  name: elasticsearch-master
spec:
  podManagementPolicy: Parallel
  replicas: 2
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      app: elasticsearch-master
  serviceName: elasticsearch-master-headless
  template:
    metadata:
      creationTimestamp: null
      labels:
        app: elasticsearch-master
        release: elasticsearch
      name: elasticsearch-master
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - elasticsearch-master
            topologyKey: kubernetes.io/hostname
      containers:
      - env:
        - name: node.name
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: metadata.name
        - name: discovery.zen.minimum_master_nodes
          value: "2"
        - name: discovery.zen.ping.unicast.hosts
          value: elasticsearch-master-headless
        - name: cluster.name
          value: elasticsearch
        - name: network.host
          value: 0.0.0.0
        - name: ES_JAVA_OPTS
          value: -Xmx1g -Xms1g
        - name: node.data
          value: "true"
        - name: node.ingest
          value: "true"
        - name: node.master
          value: "true"
        image: docker.elastic.co/elasticsearch/elasticsearch:6.8.13
        imagePullPolicy: IfNotPresent
        name: elasticsearch
        ports:
        - containerPort: 9200
          name: http
          protocol: TCP
        - containerPort: 9300
          name: transport
          protocol: TCP
        readinessProbe:
          exec:
            command:
            - sh
            - -c
            - |
              #!/usr/bin/env bash -e
              # If the node is starting up wait for the cluster to be ready (request params: "wait_for_status=green&timeout=1s" )
              # Once it has started only check that the node itself is responding
              START_FILE=/tmp/.es_start_file

              # Disable nss cache to avoid filling dentry cache when calling curl
              # This is required with Elasticsearch Docker using nss < 3.52
              export NSS_SDB_USE_CACHE=no

              http () {
                local path="${1}"
                local args="${2}"
                set -- -XGET -s

                if [ "$args" != "" ]; then
                  set -- "$@" $args
                fi

                if [ -n "${ELASTIC_USERNAME}" ] && [ -n "${ELASTIC_PASSWORD}" ]; then
                  set -- "$@" -u "${ELASTIC_USERNAME}:${ELASTIC_PASSWORD}"
                fi

                curl --output /dev/null -k "$@" "http://127.0.0.1:9200${path}"
              }

              if [ -f "${START_FILE}" ]; then
                echo 'Elasticsearch is already running, lets check the node is healthy'
                HTTP_CODE=$(http "/" "-w %{http_code}")
                RC=$?
                if [[ ${RC} -ne 0 ]]; then
                  echo "curl --output /dev/null -k -XGET -s -w '%{http_code}' \${BASIC_AUTH} http://127.0.0.1:9200/ failed with RC ${RC}"
                  exit ${RC}
                fi
                # ready if HTTP code 200, 503 is tolerable if ES version is 6.x
                if [[ ${HTTP_CODE} == "200" ]]; then
                  exit 0
                elif [[ ${HTTP_CODE} == "503" && "6" == "6" ]]; then
                  exit 0
                else
                  echo "curl --output /dev/null -k -XGET -s -w '%{http_code}' \${BASIC_AUTH} http://127.0.0.1:9200/ failed with HTTP code ${HTTP_CODE}"
                  exit 1
                fi

              else
                echo 'Waiting for elasticsearch cluster to become ready (request params: "wait_for_status=green&timeout=1s" )'
                if http "/_cluster/health?wait_for_status=green&timeout=1s" "--fail" ; then
                  touch ${START_FILE}
                  exit 0
                else
                  echo 'Cluster is not yet ready (request params: "wait_for_status=green&timeout=1s" )'
                  exit 1
                fi
              fi
          failureThreshold: 3
          initialDelaySeconds: 10
          periodSeconds: 10
          successThreshold: 3
          timeoutSeconds: 5
        resources:
          limits:
            cpu: "1"
            memory: 2Gi
          requests:
            cpu: "1"
            memory: 2Gi
        securityContext:
          capabilities:
            drop:
            - ALL
          runAsNonRoot: true
          runAsUser: 1000
        terminationMessagePath: /dev/termination-log
        terminationMessagePolicy: File
        volumeMounts:
        - mountPath: /usr/share/elasticsearch/data
          name: elasticsearch-master
      dnsPolicy: ClusterFirst
      enableServiceLinks: true
      initContainers:
      - command:
        - sysctl
        - -w
        - vm.max_map_count=262144
        image: docker.elastic.co/elasticsearch/elasticsearch:6.8.13
        imagePullPolicy: IfNotPresent
        name: configure-sysctl
        securityContext:
          privileged: true
          runAsUser: 0
        terminationMessagePath: /dev/termination-log
        terminationMessagePolicy: File
      restartPolicy: Always
      schedulerName: default-scheduler
      securityContext:
        fsGroup: 1000
        runAsUser: 1000
      terminationGracePeriodSeconds: 120
  updateStrategy:
    type: RollingUpdate
  volumeClaimTemplates:
  - apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      creationTimestamp: null
      name: elasticsearch-master
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 1Gi
      volumeMode: Filesystem
```



*elasticsearch-master-svc-example.yaml*

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    app: elasticsearch-master
    release: elasticsearch
  name: elasticsearch-master
spec:
  clusterIP:
  ports:
  - name: http
    port: 9200
  - name: transport
    port: 9300
  selector:
    app: elasticsearch-master
    release: elasticsearch
```



*elasticsearch-master-headless-svc-example.yaml*

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.alpha.kubernetes.io/tolerate-unready-endpoints: "true"
  labels:
    app: elasticsearch-master
    release: elasticsearch
  name: elasticsearch-master-headless
spec:
  clusterIP: None
  ports:
  - name: http
    port: 9200
  - name: transport
    port: 9300
  publishNotReadyAddresses: true
  selector:
    app: elasticsearch-master
```



After the above files are customized, the following example shows how can be deployed:

```
$ kubectl create ns ocean
$ kubectl config set-context --current --namespace ocean
$ kubectl apply -f elasticsearch-master-sts.yaml
$ kubectl apply -f elasticsearch-master-svc.yaml
$ kubectl apply -f elasticsearch-master-headless-svc.yaml

$ kubectl get pods,svc
NAME                         READY   STATUS    RESTARTS   AGE
pod/elasticsearch-master-0   1/1     Running   0          8h
pod/elasticsearch-master-1   1/1     Running   0          8h

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
  "name" : "elasticsearch-master-0",
  "cluster_name" : "elasticsearch",
  "cluster_uuid" : "nrv6IrPCRzu1KQ17GFuVdQ",
  "version" : {
    "number" : "6.8.13",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "be13c69",
    "build_date" : "2020-10-16T09:09:46.555371Z",
    "build_snapshot" : false,
    "lucene_version" : "7.7.3",
    "minimum_wire_compatibility_version" : "5.6.0",
    "minimum_index_compatibility_version" : "5.0.0"
  },
  "tagline" : "You Know, for Search"
}
```



##### Aquarius

For Aquarius deployment we can use the following templates for guidance.
Some parameters are [optional](https://github.com/oceanprotocol/aquarius) and the template could be adjusted based on these considerations.
One common case is the deployment for one of the following Ethereum networks:

- mainnet
- rinkeby
- ropsten

and the following template (annotated) could be edited and used for deployment.

*aquarius-standard-networks-deployment-example.yaml* (annotated)

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
      labels:
        app: aquarius
    spec:
      containers:
      - env:
        - name: LOG_LEVEL
          value: < DEBUG or INFO >
        - name: AQUARIUS_BIND_URL
          value: http://0.0.0.0:5000
        - name: AQUARIUS_WORKERS
          value: "1"
        - name: DB_HOSTNAME
          value: < Elasticsearch service >
        - name: DB_INDEX
          value: aquarius
        - name: DB_MODULE
          value: elasticsearch
        - name: DB_PORT
          value: "9200"
        - name: DB_USERNAME
          value: elastic
        - name: DB_PASSWORD
          value: changeme
        - name: DB_SSL
          value: "false"
        - name: DB_VERIFY_CERTS
          value: "false"
        - name: EVENTS_ALLOW
          value: "0"
        - name: EVENTS_RPC
          value: wss://rinkeby.infura.io/ws/v3/<YOUR-PROJECT-ID>
        - name: RUN_EVENTS_MONITOR
          value: "1"
        - name: ALLOWED_PUBLISHERS
          value: '[""]'
        - name: BFACTORY_BLOCK
          value: "< The block number of `Metadata` contract deployment >"
        - name: METADATA_CONTRACT_BLOCK
          value: "< metadata contract block >"
        - name: NETWORK_NAME
          value: < mainnet, rinkeby or ropsten >
        - name: NETWORK_URL
          value: < option selected as NETWORK_NAME above >
        - name: METADATA_UPDATE_ALL
          value: "0"
        - name: UPDATE_ALL_PURGATORY
          value: "0"
        - name: OCEAN_ADDRESS
          value: 0x8967BCF84170c91B0d24D4302C2376283b0B3a07
        image: oceanprotocol/aquarius:<tag from hub.docker.com>
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

```
$ kubectl apply -f aquarius-standard-networks-deployment.yaml
deployment.apps/aquarius created

$ kubectl get pods -l app=aquarius
NAME                        READY   STATUS    RESTARTS   AGE
aquarius-57b459946d-nxzwq   1/1     Running   0          55s
```



check the logs for newly deployed Aquarius:

```
$ kubectl logs aquarius-57b459946d-nxzwq [--follow]
[2021-02-15 19:29:23 +0000] [8] [INFO] Starting gunicorn 20.0.4
[2021-02-15 19:29:23 +0000] [8] [INFO] Listening at: http://0.0.0.0:5000 (8)
[2021-02-15 19:29:23 +0000] [8] [INFO] Using worker: gevent
[2021-02-15 19:29:23 +0000] [12] [INFO] Booting worker with pid: 12
2021-02-15 19:29:25 aquarius-57b459946d-nxzwq __main__[9] INFO EventsMonitor: preparing
2021-02-15 19:29:25 aquarius-57b459946d-nxzwq __main__[9] INFO EventsMonitor: starting with the following values: rpc=rinkeby
default log level: 20, env var LOG_LEVEL INFO
.............................................................
2021-02-15 19:29:26 aquarius-57b459946d-nxzwq __main__[9] INFO EventsMonitor: started
................................................................
2021-02-15 19:29:48,049 - aquarius.events.events_monitor - INFO - Start processing MetadataCreated event: did=did:op:e3156E12a379Eccfa8ceA824dc3085220E0c65aB
2021-02-15 19:29:48,050 - aquarius - INFO - got event MetadataCreated request: {'@context': 'https://w3id.org/did/v1', 'id': 'did:op:e3156E12a379Eccfa8ceA824dc3085220E0c65aB', 'publicKey': [{'id': 'did:op:e3156E12a379Eccfa8ceA824dc3085220E0c65aB', 'type': 'EthereumECDSAKey', 'owner': '0xC7EC1970B09224B317c52d92f37F5e1E4fF6B687'}], 'authentication': [{'type': 'RsaSignatureAuthentication2018', 'publicKey': 'did:op:e3156E12a379Eccfa8ceA824dc3085220E0c65aB'}], 'service': [{'type': 'metadata', 'attributes': {'curation': {'rating': 0, 'numVotes': 0}, 'main': {'type': 'dataset', 'name': 'Pool fee test - default - 10%', 'dateCreated': '2020-10-05T19:08:28Z', 'author': 'Alex', 'license': 'Public Domain', 'files': [{'contentLength': '2989228', 'contentType': 'application/pdf', 'index': 0}], 'datePublished': '2020-10-05T19:08:28Z'}, 'additionalInformation': {'description': 'Pool setup with 1% swap fee', 'copyrightHolder': 'Ocean Protocol', 'tags': [''], 'links': False, 'termsAndConditions': True, 'priceType': 'dynamic'}, 'encryptedFiles': '0x04f78f25a27009245cd7f471731c1a9faac812240379b925ed4d01f6a365924c85930c7a5698edade296f4bd7df3d60a9fc1a3915e38cbf55a5009e3788ae53843ebb86063489e2a2a3047324e7509f2cc60e3a22def41b81700023b48753e028c20d807d2ff4305e3885470a730f3519f9158ba134f4b34cffd6d41618b73be8f76c2ea76a3ef7c8506406278baeec8527ca76ae567845d60b6f968d4116db3ec77dfabd016c285eb5bf0b66059c053c2c951364fa468d1b972f4640e70c6dd8df5f524838a8ab1dfa5fa4128a9349e17b44083'}, 'index': 0}, {'type': 'access', 'index': 1, 'serviceEndpoint': 'https://provider.rinkeby.v3.dev-ocean.com', 'attributes': {'main': {'creator': '0xC7EC1970B09224B317c52d92f37F5e1E4fF6B687', 'datePublished': '2020-10-05T19:08:28Z', 'cost': '1', 'timeout': 0, 'name': 'dataAssetAccess'}}}], 'dataToken': '0xe3156E12a379Eccfa8ceA824dc3085220E0c65aB', 'created': '2020-10-05T19:08:50Z', 'proof': {'created': '2020-10-05T19:08:53Z', 'creator': '0xC7EC1970B09224B317c52d92f37F5e1E4fF6B687', 'type': 'DDOIntegritySignature', 'signatureValue': '0x8feb4ea129dcda520867e3dce0e0cb309da9c6fd56a1f49dafa069492ac7e4f328b21b5cb8a61d9e979c48bbcdcac8b25e2f536e7da4712c867461d5a90590c61c'}}
```



next step is to create a [service](https://kubernetes.io/docs/concepts/services-networking/service/) (eg. ClusterIP,  NodePort,  Loadbalancer, ExternalName) for this deployment depending on environment specs.



#### Docker Compose deployment



##### Single systemd service (Aquarius+Elasticsearch)

a) create */etc/docker/compose/aquarius/docker-compose.yml* file

 */etc/docker/compose/aquarius/docker-compose.yml* (annotated - this example use ropsten network)

```yaml
version: '3'
services:
  elasticsearch:
    image: elasticsearch:6.8.13
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
      - backend

  aquarius:
    image: oceanprotocol/aquarius:v2.2.6
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
      DB_HOSTNAME: elasticsearch
      DB_PORT: 9200
      DB_USERNAME: elastic
      DB_PASSWORD: changeme
      LOG_LEVEL: "DEBUG"
      NETWORK_NAME: "ropsten"
      NETWORK_URL: "ropsten"
      EVENTS_RPC: "ropsten"
      BFACTORY_BLOCK: 9227563
      METADATA_CONTRACT_BLOCK: 9227563
      EVENTS_ALLOW: 0
      RUN_EVENTS_MONITOR: 1
volumes:
  data:
    driver: local
networks:
  backend:
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
● docker-compose@aquarius.service - aquarius service with docker compose
   Loaded: loaded (/etc/systemd/system/docker-compose@aquarius.service; disabled; vendor preset: disabled)
   Active: active (exited) since Tue 2021-03-30 10:31:52 UTC; 1s ago
  Process: 9625 ExecStart=/usr/bin/env docker-compose -p $PROJECT up -d --remove-orphans (code=exited, status=0/SUCCESS)
  Process: 9611 ExecStartPre=/usr/bin/env docker-compose -p $PROJECT pull (code=exited, status=0/SUCCESS)
 Main PID: 9625 (code=exited, status=0/SUCCESS)

Mar 30 10:31:50 ip-172-31-32-61.eu-central-1.compute.internal env[9611]: Pulling aquarius      ... status: image is up to date for o...
Mar 30 10:31:50 ip-172-31-32-61.eu-central-1.compute.internal env[9611]: Pulling aquarius      ... done
Mar 30 10:31:50 ip-172-31-32-61.eu-central-1.compute.internal env[9625]: Building with native build. Learn about native build in Compose here: https://docs.docker.com/go/compose-native-build/
Mar 30 10:31:50 ip-172-31-32-61.eu-central-1.compute.internal env[9625]: Creating network "ocean_backend" with driver "bridge"
Mar 30 10:31:51 ip-172-31-32-61.eu-central-1.compute.internal env[9625]: Creating volume "ocean_data" with local driver
Mar 30 10:31:51 ip-172-31-32-61.eu-central-1.compute.internal env[9625]: Creating elasticsearch ...
Mar 30 10:31:51 ip-172-31-32-61.eu-central-1.compute.internal env[9625]: Creating elasticsearch ... done
Mar 30 10:31:51 ip-172-31-32-61.eu-central-1.compute.internal env[9625]: Creating aquarius      ...
Mar 30 10:31:52 ip-172-31-32-61.eu-central-1.compute.internal env[9625]: Creating aquarius      ... done
Mar 30 10:31:52 ip-172-31-32-61.eu-central-1.compute.internal systemd[1]: Started aquarius service with docker compose.
```





```shell
$ curl localhost:9200
{
  "name" : "Xgds4l1",
  "cluster_name" : "docker-cluster",
  "cluster_uuid" : "KmazJdkmQSG8MMAetuTKlQ",
  "version" : {
    "number" : "6.8.13",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "be13c69",
    "build_date" : "2020-10-16T09:09:46.555371Z",
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
{"plugin":"elasticsearch","software":"Aquarius","version":"2.2.6"}
```



use docker cli to check aquarius service logs:

== identify container id

```shell
$ docker ps
CONTAINER ID   IMAGE                           COMMAND                  CREATED         STATUS         PORTS                              NAMES
c169936afc46   oceanprotocol/aquarius:v2.2.6   "/aquarius/docker-en…"   2 minutes ago   Up 2 minutes   0.0.0.0:5000->5000/tcp             aquarius
fe4df7fbc3e6   elasticsearch:6.8.13            "/usr/local/bin/dock…"   2 minutes ago   Up 2 minutes   0.0.0.0:9200->9200/tcp, 9300/tcp   elasticsearch

```



== check logs from aquarius docker container

```shell
$ docker logs c169936afc46 [--follow]
[2021-03-30 10:31:52 +0000] [9] [INFO] Starting gunicorn 20.0.4
[2021-03-30 10:31:52 +0000] [9] [INFO] Listening at: http://0.0.0.0:5000 (9)
[2021-03-30 10:31:52 +0000] [9] [INFO] Using worker: gevent
[2021-03-30 10:31:52 +0000] [35] [INFO] Booting worker with pid: 35
[2021-03-30 10:31:53 +0000] [40] [INFO] Booting worker with pid: 40
[2021-03-30 10:31:53 +0000] [44] [INFO] Booting worker with pid: 44
[2021-03-30 10:31:53 +0000] [47] [INFO] Booting worker with pid: 47
[2021-03-30 10:31:53 +0000] [51] [INFO] Booting worker with pid: 51
[2021-03-30 10:31:53 +0000] [53] [INFO] Booting worker with pid: 53
[2021-03-30 10:31:53 +0000] [55] [INFO] Booting worker with pid: 55
[2021-03-30 10:31:53 +0000] [58] [INFO] Booting worker with pid: 58
2021-03-30 10:32:01 c169936afc46 __main__[10] INFO EventsMonitor: preparing
2021-03-30 10:32:01 c169936afc46 __main__[10] INFO EventsMonitor: starting with the following values: rpc=ropsten
2021-03-30 10:32:01 c169936afc46 root[10] INFO Trying to connect...
2021-03-30 10:32:06 c169936afc46 root[10] INFO Trying to connect...
2021-03-30 10:32:07 c169936afc46 root[44] INFO Trying to connect...
2021-03-30 10:32:07 c169936afc46 root[40] INFO Trying to connect...
2021-03-30 10:32:07 c169936afc46 root[35] INFO Trying to connect...
2021-03-30 10:32:07 c169936afc46 root[47] INFO Trying to connect...
2021-03-30 10:32:07 c169936afc46 root[55] INFO Trying to connect...
2021-03-30 10:32:07 c169936afc46 root[58] INFO Trying to connect...
2021-03-30 10:32:07 c169936afc46 root[53] INFO Trying to connect...
2021-03-30 10:32:08 c169936afc46 root[51] INFO Trying to connect...
2021-03-30 10:32:11 c169936afc46 root[10] INFO Trying to connect...
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:12,793 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 10:32:12,793 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:13,392 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 10:32:13,393 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:13,438 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 10:32:13,439 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:13,468 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 10:32:13,468 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:13,478 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 10:32:13,479 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:13,486 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 10:32:13,487 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:13,533 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 10:32:13,533 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:13,541 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 10:32:13,547 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 10:32:16,655 - aquarius.events.metadata_updater - DEBUG - Ocean token address: 0x5e8DCB2AfA23844bcc311B00Ad1A0C30025aADE9,
all deployed addresses: dict_items([('DTFactory', '0x6ebcCa6df2CAba986FCF44E64Ee82251c1455Dcc'), ('BFactory', '0x75be6e18c80A487C8b49663bf14f80A6495045B2'), ('FixedRateExchange', '0xA7a711A09396DF82D9be46A26B48BafdB9BB4fA6'), ('Metadata', '0x3cd7Ef1F207E1a46AAd7D5d7F5f0A5cF081Fc726'), ('Ocean', '0x5e8DCB2AfA23844bcc311B00Ad1A0C30025aADE9')])
2021-03-30 10:32:18,386 - aquarius.events.events_monitor - DEBUG - allowed publishers: set()
2021-03-30 10:32:18,386 - aquarius.events.events_monitor - DEBUG - EventsMonitor: using Metadata contract address 0x3cd7Ef1F207E1a46AAd7D5d7F5f0A5cF081Fc726.
2021-03-30 10:32:18,386 - aquarius.events.events_monitor - INFO - Starting the events monitor on contract 0x3cd7Ef1F207E1a46AAd7D5d7F5f0A5cF081Fc726.
/usr/local/lib/python3.8/dist-packages/elasticsearch/connection/base.py:200: ElasticsearchWarning: [types removal] The parameter include_type_name should be explicitly specified in create index requests to prepare for 7.0. In 7.0 include_type_name will default to 'false', and requests are expected to omit the type name in mapping definitions.
  warnings.warn(message, category=ElasticsearchWarning)
/usr/local/lib/python3.8/dist-packages/elasticsearch/connection/base.py:200: ElasticsearchWarning: the default number of shards will change from [5] to [1] in 7.0.0; if you wish to continue using the default of [5] shards, you must manage this on the create index request or with an index template
  warnings.warn(message, category=ElasticsearchWarning)
2021-03-30 10:32:18 c169936afc46 __main__[10] INFO EventsMonitor: started
2021-03-30 10:32:18,844 - aquarius.events.events_monitor - DEBUG - Metadata monitor >>>> from_block:9227563, current_block:9942343 <<<<
2021-03-30 10:32:18,844 - aquarius.events.events_monitor - DEBUG - get_event_logs (MetadataCreated, 9227563, 9942343)..
2021-03-30 10:32:19,639 - aquarius.events.events_monitor - INFO - Process new DDO, did from event log:did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af, sender:0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7
2021-03-30 10:32:19,639 - aquarius.events.events_monitor - DEBUG - checking allowed publishers: 0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7
2021-03-30 10:32:19,643 - aquarius.events.events_monitor - INFO - Start processing MetadataCreated event: did=did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af
2021-03-30 10:32:19,643 - aquarius.events.events_monitor - DEBUG - block 9232523, contract: 0x3cd7Ef1F207E1a46AAd7D5d7F5f0A5cF081Fc726, Sender: 0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7 , txid: 0xe86b1d17f1b92c8717483c3d48721edab8e48350df3e6180b7864558e3a9e6ec
2021-03-30 10:32:19,643 - aquarius.events.events_monitor - DEBUG - decoding with did did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af and flags b'\x01'
2021-03-30 10:32:19,643 - aquarius.events.events_monitor - DEBUG - flags: b'\x01'
2021-03-30 10:32:19,643 - aquarius.events.events_monitor - DEBUG - checkflags: 1
2021-03-30 10:32:19,644 - aquarius.events.events_monitor - DEBUG - Decompressed to b'{\n  "@context": "https://w3id.org/did/v1",\n  "id": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n  "publicKey": [\n    {\n      "id": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n      "type": "EthereumECDSAKey",\n      "owner": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7"\n    }\n  ],\n  "authentication": [\n    {\n      "type": "RsaSignatureAuthentication2018",\n      "publicKey": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af"\n    }\n  ],\n  "service": [\n    {\n      "type": "metadata",\n      "attributes": {\n        "curation": {\n          "rating": 0,\n          "numVotes": 0\n        },\n        "main": {\n          "type": "dataset",\n          "name": "Maritime Word List",\n          "dateCreated": "2020-12-10T09:41:01Z",\n          "author": "Ocean Team",\n          "license": "https://market.oceanprotocol.com/terms",\n          "files": [\n            {\n              "contentLength": "3215",\n              "contentType": "text/plain",\n              "index": 0\n            }\n          ],\n          "datePublished": "2020-12-10T09:41:01Z"\n        },\n        "additionalInformation": {\n          "description": "The wordlist used by ocean.js to generate datatoken names within the Ocean Protocol ecosystem.\\n\\n### Data Structure\\n\\nThe json object holds 2 arrays of strings, nouns and adjectives.\\n\\n```json\\n{\\n  \\"nouns\\": [ \\"Crab\\", \\"Fish\\", \\"Shark\\"],\\n  \\"adjectives\\": [ \\"adamant\\", \\"adroit\\" ]\\n}\\n```",\n          "tags": [\n            "wordlist",\n            "animals"\n          ],\n          "links": [\n            {\n              "contentLength": "74",\n              "contentType": "text/plain",\n              "url": "https://ipfs.oceanprotocol.com/ipfs/QmWTpf5JXyAEfNyuBHc9Gey6pw4WKx6GfJs5efMSyMGwza"\n            }\n          ],\n          "termsAndConditions": true\n        },\n        "encryptedFiles": "0x04e164b38786f9c2049ca54950e2693b2a6116a09066068c803310635baaf703e757075960fe534db0c4426f3ad736a60576218721ad68e6b98dec9a0cdaa4324a23fd1ab404fdd2b7e2395fa72bd5885c02b78e0b99bbf404e3b2f129010cc1ab97e0a3b11e26b51961aa595a7c90c40a713d8eb856b356f06f7eef087caf2ee2fad3c0fc0283a47a770f3bd2ac3f707f3144af62cca13f9343e00f8971192c47f09a57d55b6811489b8109f0ab0d0d37ee6516547014cd0fc5b403e246afebeaaddabb56d0e392e6bac81d75e723c65bbda7b2fff91f538cfb9d97a2478ab3a9ff371db716c389c9fd0bdfe7164053"\n      },\n      "index": 0\n    },\n    {\n      "type": "access",\n      "index": 1,\n      "serviceEndpoint": "https://provider.ropsten.oceanprotocol.com",\n      "attributes": {\n        "main": {\n          "creator": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7",\n          "datePublished": "2020-12-10T09:41:01Z",\n          "cost": "1",\n          "timeout": 0,\n          "name": "dataAssetAccess"\n        }\n      }\n    }\n  ],\n  "dataToken": "0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n  "created": "2020-12-10T09:42:06Z",\n  "proof": {\n    "created": "2020-12-10T09:42:06Z",\n    "creator": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7",\n    "type": "AddressHash",\n    "signatureValue": "0x6184e0f6a704c90afbd37682a28963da55325c66c390a609e313934596f63b43"\n  },\n  "dataTokenInfo": {\n    "name": "Wheedling Penguin Token",\n    "symbol": "WHEPEN-58",\n    "address": "0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n    "cap": 1000\n  }\n}'
2021-03-30 10:32:19,644 - aquarius.events.events_monitor - DEBUG - After unpack rawddo:b'{\n  "@context": "https://w3id.org/did/v1",\n  "id": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n  "publicKey": [\n    {\n      "id": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n      "type": "EthereumECDSAKey",\n      "owner": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7"\n    }\n  ],\n  "authentication": [\n    {\n      "type": "RsaSignatureAuthentication2018",\n      "publicKey": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af"\n    }\n  ],\n  "service": [\n    {\n      "type": "metadata",\n      "attributes": {\n        "curation": {\n          "rating": 0,\n          "numVotes": 0\n        },\n        "main": {\n          "type": "dataset",\n          "name": "Maritime Word List",\n          "dateCreated": "2020-12-10T09:41:01Z",\n          "author": "Ocean Team",\n          "license": "https://market.oceanprotocol.com/terms",\n          "files": [\n            {\n              "contentLength": "3215",\n              "contentType": "text/plain",\n              "index": 0\n            }\n          ],\n          "datePublished": "2020-12-10T09:41:01Z"\n        },\n        "additionalInformation": {\n          "description": "The wordlist used by ocean.js to generate datatoken names within the Ocean Protocol ecosystem.\\n\\n### Data Structure\\n\\nThe json object holds 2 arrays of strings, nouns and adjectives.\\n\\n```json\\n{\\n  \\"nouns\\": [ \\"Crab\\", \\"Fish\\", \\"Shark\\"],\\n  \\"adjectives\\": [ \\"adamant\\", \\"adroit\\" ]\\n}\\n```",\n          "tags": [\n            "wordlist",\n            "animals"\n          ],\n          "links": [\n            {\n              "contentLength": "74",\n              "contentType": "text/plain",\n              "url": "https://ipfs.oceanprotocol.com/ipfs/QmWTpf5JXyAEfNyuBHc9Gey6pw4WKx6GfJs5efMSyMGwza"\n            }\n          ],\n          "termsAndConditions": true\n        },\n        "encryptedFiles": "0x04e164b38786f9c2049ca54950e2693b2a6116a09066068c803310635baaf703e757075960fe534db0c4426f3ad736a60576218721ad68e6b98dec9a0cdaa4324a23fd1ab404fdd2b7e2395fa72bd5885c02b78e0b99bbf404e3b2f129010cc1ab97e0a3b11e26b51961aa595a7c90c40a713d8eb856b356f06f7eef087caf2ee2fad3c0fc0283a47a770f3bd2ac3f707f3144af62cca13f9343e00f8971192c47f09a57d55b6811489b8109f0ab0d0d37ee6516547014cd0fc5b403e246afebeaaddabb56d0e392e6bac81d75e723c65bbda7b2fff91f538cfb9d97a2478ab3a9ff371db716c389c9fd0bdfe7164053"\n      },\n      "index": 0\n    },\n    {\n      "type": "access",\n      "index": 1,\n      "serviceEndpoint": "https://provider.ropsten.oceanprotocol.com",\n      "attributes": {\n        "main": {\n          "creator": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7",\n          "datePublished": "2020-12-10T09:41:01Z",\n          "cost": "1",\n          "timeout": 0,\n          "name": "dataAssetAccess"\n        }\n      }\n    }\n  ],\n  "dataToken": "0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n  "created": "2020-12-10T09:42:06Z",\n  "proof": {\n    "created": "2020-12-10T09:42:06Z",\n    "creator": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7",\n    "type": "AddressHash",\n    "signatureValue": "0x6184e0f6a704c90afbd37682a28963da55325c66c390a609e313934596f63b43"\n  },\n  "dataTokenInfo": {\n    "name": "Wheedling Penguin Token",\n    "symbol": "WHEPEN-58",\n    "address": "0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n    "cap": 1000\n  }\n}'
2021-03-30 10:32:19,644 - aquarius - INFO - got event MetadataCreated request: {'@context': 'https://w3id.org/did/v1', 'id': 'did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af', 'publicKey': [{'id': 'did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af', 'type': 'EthereumECDSAKey', 'owner': '0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7'}], 'authentication': [{'type': 'RsaSignatureAuthentication2018', 'publicKey': 'did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af'}], 'service': [{'type': 'metadata', 'attributes': {'curation': {'rating': 0, 'numVotes': 0}, 'main': {'type': 'dataset', 'name': 'Maritime Word List', 'dateCreated': '2020-12-10T09:41:01Z', 'author': 'Ocean Team', 'license': 'https://market.oceanprotocol.com/terms', 'files': [{'contentLength': '3215', 'contentType': 'text/plain', 'index': 0}], 'datePublished': '2020-12-10T09:41:01Z'}, 'additionalInformation': {'description': 'The wordlist used by ocean.js to generate datatoken names within the Ocean Protocol ecosystem.\n\n### Data Structure\n\nThe json object holds 2 arrays of strings, nouns and adjectives.\n\n```json\n{\n  "nouns": [ "Crab", "Fish", "Shark"],\n  "adjectives": [ "adamant", "adroit" ]\n}\n```', 'tags': ['wordlist', 'animals'], 'links': [{'contentLength': '74', 'contentType': 'text/plain', 'url': 'https://ipfs.oceanprotocol.com/ipfs/QmWTpf5JXyAEfNyuBHc9Gey6pw4WKx6GfJs5efMSyMGwza'}], 'termsAndConditions': True}, 'encryptedFiles': '0x04e164b38786f9c2049ca54950e2693b2a6116a09066068c803310635baaf703e757075960fe534db0c4426f3ad736a60576218721ad68e6b98dec9a0cdaa4324a23fd1ab404fdd2b7e2395fa72bd5885c02b78e0b99bbf404e3b2f129010cc1ab97e0a3b11e26b51961aa595a7c90c40a713d8eb856b356f06f7eef087caf2ee2fad3c0fc0283a47a770f3bd2ac3f707f3144af62cca13f9343e00f8971192c47f09a57d55b6811489b8109f0ab0d0d37ee6516547014cd0fc5b403e246afebeaaddabb56d0e392e6bac81d75e723c65bbda7b2fff91f538cfb9d97a2478ab3a9ff371db716c389c9fd0bdfe7164053'}, 'index': 0}, {'type': 'access', 'index': 1, 'serviceEndpoint': 'https://provider.ropsten.oceanprotocol.com', 'attributes': {'main': {'creator': '0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7', 'datePublished': '2020-12-10T09:41:01Z', 'cost': '1', 'timeout': 0, 'name': 'dataAssetAccess'}}}], 'dataToken': '0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af', 'created': '2020-12-10T09:42:06Z', 'proof': {'created': '2020-12-10T09:42:06Z', 'creator': '0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7', 'type': 'AddressHash', 'signatureValue': '0x6184e0f6a704c90afbd37682a28963da55325c66c390a609e313934596f63b43'}, 'dataTokenInfo': {'name': 'Wheedling Penguin Token', 'symbol': 'WHEPEN-58', 'address': '0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af', 'cap': 1000}}
.....................................................................................
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
    image: elasticsearch:6.8.13
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
    image: oceanprotocol/aquarius:v2.2.6 ==> specificy version (check on https://hub.docker.com/r/oceanprotocol/aquarius )
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
      LOG_LEVEL: "DEBUG"
      NETWORK_NAME: "ropsten"
      NETWORK_URL: "ropsten"
      EVENTS_RPC: "ropsten"
      BFACTORY_BLOCK: 9227563
      METADATA_CONTRACT_BLOCK: 9227563
      EVENTS_ALLOW: 0
      RUN_EVENTS_MONITOR: 1
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
● docker-compose@elasticsearch.service - elasticsearch service with docker compose
   Loaded: loaded (/etc/systemd/system/docker-compose@elasticsearch.service; enabled; vendor preset: disabled)
   Active: active (exited) since Tue 2021-03-30 07:24:41 UTC; 6s ago
  Process: 10918 ExecStop=/usr/bin/env docker-compose -p $PROJECT stop (code=exited, status=0/SUCCESS)
  Process: 11063 ExecStart=/usr/bin/env docker-compose -p $PROJECT up -d --remove-orphans (code=exited, status=0/SUCCESS)
  Process: 11050 ExecStartPre=/usr/bin/env docker-compose -p $PROJECT pull (code=exited, status=0/SUCCESS)
 Main PID: 11063 (code=exited, status=0/SUCCESS)

Mar 30 07:24:39 ip-172-31-32-61.eu-central-1.compute.internal env[11050]: Pulling elasticsearch ... pulling from library/elasticsearch
Mar 30 07:24:39 ip-172-31-32-61.eu-central-1.compute.internal env[11050]: Pulling elasticsearch ... digest: sha256:8d4e29332dc159e7c2...
Mar 30 07:24:39 ip-172-31-32-61.eu-central-1.compute.internal env[11050]: Pulling elasticsearch ... status: image is up to date for e...
Mar 30 07:24:39 ip-172-31-32-61.eu-central-1.compute.internal env[11050]: Pulling elasticsearch ... done
Mar 30 07:24:40 ip-172-31-32-61.eu-central-1.compute.internal env[11063]: Building with native build. Learn about native build in Compose here: https://docs.docker.com/go/compose-native-build/
Mar 30 07:24:40 ip-172-31-32-61.eu-central-1.compute.internal env[11063]: Creating network "ocean_backend" with driver "bridge"
Mar 30 07:24:40 ip-172-31-32-61.eu-central-1.compute.internal env[11063]: Creating volume "ocean_data" with local driver
Mar 30 07:24:40 ip-172-31-32-61.eu-central-1.compute.internal env[11063]: Creating elasticsearch ...
Mar 30 07:24:41 ip-172-31-32-61.eu-central-1.compute.internal env[11063]: Creating elasticsearch ... done
Mar 30 07:24:41 ip-172-31-32-61.eu-central-1.compute.internal systemd[1]: Started elasticsearch service with docker compose.
```



confirm Elasticsearch service is accessible on localhost port 9200/tcp

```shell
$ curl localhost:9200
{
  "name" : "iHs_ltW",
  "cluster_name" : "docker-cluster",
  "cluster_uuid" : "dHDN3-LIQAi4JzI8yOqsjw",
  "version" : {
    "number" : "6.8.13",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "be13c69",
    "build_date" : "2020-10-16T09:09:46.555371Z",
    "build_snapshot" : false,
    "lucene_version" : "7.7.3",
    "minimum_wire_compatibility_version" : "5.6.0",
    "minimum_index_compatibility_version" : "5.0.0"
  },
  "tagline" : "You Know, for Search"
}
```



g) start Aquarius service:

```
$ sudo systemctl start docker-compose@aquarius.service
```



check the status:

```shell
$ sudo systemctl status docker-compose@aquarius.service
● docker-compose@aquarius.service - aquarius service with docker compose
   Loaded: loaded (/etc/systemd/system/docker-compose@aquarius.service; enabled; vendor preset: disabled)
   Active: active (exited) since Tue 2021-03-30 07:28:36 UTC; 5s ago
  Process: 10778 ExecStopPost=/usr/bin/env docker-compose down (code=exited, status=0/SUCCESS)
  Process: 10736 ExecStop=/usr/bin/env docker-compose stop (code=exited, status=0/SUCCESS)
  Process: 11361 ExecStart=/usr/bin/env docker-compose up -d --remove-orphans (code=exited, status=0/SUCCESS)
  Process: 11349 ExecStartPre=/usr/bin/env docker-compose pull (code=exited, status=0/SUCCESS)
 Main PID: 11361 (code=exited, status=0/SUCCESS)

Mar 30 07:28:33 ip-172-31-32-61.eu-central-1.compute.internal systemd[1]: Starting aquarius service with docker compose...
Mar 30 07:28:34 ip-172-31-32-61.eu-central-1.compute.internal env[11349]: Pulling aquarius ...
Mar 30 07:28:35 ip-172-31-32-61.eu-central-1.compute.internal env[11349]: Pulling aquarius ... pulling from oceanprotocol/aquarius
Mar 30 07:28:35 ip-172-31-32-61.eu-central-1.compute.internal env[11349]: Pulling aquarius ... digest: sha256:072140335817e56d61...
Mar 30 07:28:35 ip-172-31-32-61.eu-central-1.compute.internal env[11349]: Pulling aquarius ... status: image is up to date for o...
Mar 30 07:28:35 ip-172-31-32-61.eu-central-1.compute.internal env[11349]: Pulling aquarius ... done
Mar 30 07:28:36 ip-172-31-32-61.eu-central-1.compute.internal env[11361]: Building with native build. Learn about native build in Compose here: https://docs.docker.com/go/compose-native-build/
Mar 30 07:28:36 ip-172-31-32-61.eu-central-1.compute.internal env[11361]: Creating aquarius ...
Mar 30 07:28:36 ip-172-31-32-61.eu-central-1.compute.internal env[11361]: Creating aquarius ... done
Mar 30 07:28:36 ip-172-31-32-61.eu-central-1.compute.internal systemd[1]: Started aquarius service with docker compose.
```



use docker cli to check aquarius service logs:

== identify container id

```shell
$ docker ps
CONTAINER ID   IMAGE                           COMMAND                  CREATED          STATUS          PORTS                              NAMES
f44327bd3c33   oceanprotocol/aquarius:v2.2.6   "/aquarius/docker-en…"   18 seconds ago   Up 18 seconds   0.0.0.0:5000->5000/tcp             aquarius
9b4c260619ca   elasticsearch:6.8.13            "/usr/local/bin/dock…"   4 minutes ago    Up 4 minutes    0.0.0.0:9200->9200/tcp, 9300/tcp   elasticsearch

```



== check logs from aquarius docker container

```shell
$ docker logs f44327bd3c33 [--follow]
[2021-03-30 07:28:36 +0000] [10] [INFO] Starting gunicorn 20.0.4
[2021-03-30 07:28:36 +0000] [10] [INFO] Listening at: http://0.0.0.0:5000 (10)
[2021-03-30 07:28:36 +0000] [10] [INFO] Using worker: gevent
[2021-03-30 07:28:36 +0000] [13] [INFO] Booting worker with pid: 13
[2021-03-30 07:28:36 +0000] [16] [INFO] Booting worker with pid: 16
[2021-03-30 07:28:37 +0000] [24] [INFO] Booting worker with pid: 24
[2021-03-30 07:28:37 +0000] [26] [INFO] Booting worker with pid: 26
[2021-03-30 07:28:37 +0000] [29] [INFO] Booting worker with pid: 29
[2021-03-30 07:28:37 +0000] [32] [INFO] Booting worker with pid: 32
[2021-03-30 07:28:37 +0000] [36] [INFO] Booting worker with pid: 36
[2021-03-30 07:28:37 +0000] [39] [INFO] Booting worker with pid: 39
2021-03-30 07:28:42 f44327bd3c33 __main__[11] INFO EventsMonitor: preparing
2021-03-30 07:28:42 f44327bd3c33 __main__[11] INFO EventsMonitor: starting with the following values: rpc=ropsten
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:44,689 - aquarius.events.metadata_updater - DEBUG - Ocean token address: 0x5e8DCB2AfA23844bcc311B00Ad1A0C30025aADE9,
all deployed addresses: dict_items([('DTFactory', '0x6ebcCa6df2CAba986FCF44E64Ee82251c1455Dcc'), ('BFactory', '0x75be6e18c80A487C8b49663bf14f80A6495045B2'), ('FixedRateExchange', '0xA7a711A09396DF82D9be46A26B48BafdB9BB4fA6'), ('Metadata', '0x3cd7Ef1F207E1a46AAd7D5d7F5f0A5cF081Fc726'), ('Ocean', '0x5e8DCB2AfA23844bcc311B00Ad1A0C30025aADE9')])
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:45,735 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 07:28:45,736 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:46,076 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 07:28:46,077 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:46,116 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 07:28:46,116 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:46,581 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 07:28:46,581 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:46,616 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 07:28:46,617 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:46,712 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 07:28:46,712 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:46,742 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 07:28:46,742 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
default log level: 10, env var LOG_LEVEL DEBUG
2021-03-30 07:28:46,812 - aquarius.config - DEBUG - Config: loading config file /aquarius/config.ini
2021-03-30 07:28:46,812 - aquarius.config - DEBUG - Config: setting environ aquarius.url = http://0.0.0.0:5000
2021-03-30 07:28:46,832 - aquarius.events.events_monitor - DEBUG - allowed publishers: set()
2021-03-30 07:28:46,832 - aquarius.events.events_monitor - DEBUG - EventsMonitor: using Metadata contract address 0x3cd7Ef1F207E1a46AAd7D5d7F5f0A5cF081Fc726.
2021-03-30 07:28:46,833 - aquarius.events.events_monitor - INFO - Starting the events monitor on contract 0x3cd7Ef1F207E1a46AAd7D5d7F5f0A5cF081Fc726.
/usr/local/lib/python3.8/dist-packages/elasticsearch/connection/base.py:200: ElasticsearchWarning: the default number of shards will change from [5] to [1] in 7.0.0; if you wish to continue using the default of [5] shards, you must manage this on the create index request or with an index template
  warnings.warn(message, category=ElasticsearchWarning)
/usr/local/lib/python3.8/dist-packages/elasticsearch/connection/base.py:200: ElasticsearchWarning: [types removal] The parameter include_type_name should be explicitly specified in create index requests to prepare for 7.0. In 7.0 include_type_name will default to 'false', and requests are expected to omit the type name in mapping definitions.
  warnings.warn(message, category=ElasticsearchWarning)
2021-03-30 07:28:46 f44327bd3c33 __main__[11] INFO EventsMonitor: started
2021-03-30 07:28:47,290 - aquarius.events.events_monitor - DEBUG - Metadata monitor >>>> from_block:9227563, current_block:9941287 <<<<
2021-03-30 07:28:47,290 - aquarius.events.events_monitor - DEBUG - get_event_logs (MetadataCreated, 9227563, 9941287)..
2021-03-30 07:28:48,098 - aquarius.events.events_monitor - INFO - Process new DDO, did from event log:did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af, sender:0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7
2021-03-30 07:28:48,098 - aquarius.events.events_monitor - DEBUG - checking allowed publishers: 0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7
2021-03-30 07:28:48,102 - aquarius.events.events_monitor - INFO - Start processing MetadataCreated event: did=did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af
2021-03-30 07:28:48,102 - aquarius.events.events_monitor - DEBUG - block 9232523, contract: 0x3cd7Ef1F207E1a46AAd7D5d7F5f0A5cF081Fc726, Sender: 0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7 , txid: 0xe86b1d17f1b92c8717483c3d48721edab8e48350df3e6180b7864558e3a9e6ec
2021-03-30 07:28:48,102 - aquarius.events.events_monitor - DEBUG - decoding with did did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af and flags b'\x01'
2021-03-30 07:28:48,102 - aquarius.events.events_monitor - DEBUG - flags: b'\x01'
2021-03-30 07:28:48,102 - aquarius.events.events_monitor - DEBUG - checkflags: 1
2021-03-30 07:28:48,104 - aquarius.events.events_monitor - DEBUG - Decompressed to b'{\n  "@context": "https://w3id.org/did/v1",\n  "id": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n  "publicKey": [\n    {\n      "id": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n      "type": "EthereumECDSAKey",\n      "owner": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7"\n    }\n  ],\n  "authentication": [\n    {\n      "type": "RsaSignatureAuthentication2018",\n      "publicKey": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af"\n    }\n  ],\n  "service": [\n    {\n      "type": "metadata",\n      "attributes": {\n        "curation": {\n          "rating": 0,\n          "numVotes": 0\n        },\n        "main": {\n          "type": "dataset",\n          "name": "Maritime Word List",\n          "dateCreated": "2020-12-10T09:41:01Z",\n          "author": "Ocean Team",\n          "license": "https://market.oceanprotocol.com/terms",\n          "files": [\n            {\n              "contentLength": "3215",\n              "contentType": "text/plain",\n              "index": 0\n            }\n          ],\n          "datePublished": "2020-12-10T09:41:01Z"\n        },\n        "additionalInformation": {\n          "description": "The wordlist used by ocean.js to generate datatoken names within the Ocean Protocol ecosystem.\\n\\n### Data Structure\\n\\nThe json object holds 2 arrays of strings, nouns and adjectives.\\n\\n```json\\n{\\n  \\"nouns\\": [ \\"Crab\\", \\"Fish\\", \\"Shark\\"],\\n  \\"adjectives\\": [ \\"adamant\\", \\"adroit\\" ]\\n}\\n```",\n          "tags": [\n            "wordlist",\n            "animals"\n          ],\n          "links": [\n            {\n              "contentLength": "74",\n              "contentType": "text/plain",\n              "url": "https://ipfs.oceanprotocol.com/ipfs/QmWTpf5JXyAEfNyuBHc9Gey6pw4WKx6GfJs5efMSyMGwza"\n            }\n          ],\n          "termsAndConditions": true\n        },\n        "encryptedFiles": "0x04e164b38786f9c2049ca54950e2693b2a6116a09066068c803310635baaf703e757075960fe534db0c4426f3ad736a60576218721ad68e6b98dec9a0cdaa4324a23fd1ab404fdd2b7e2395fa72bd5885c02b78e0b99bbf404e3b2f129010cc1ab97e0a3b11e26b51961aa595a7c90c40a713d8eb856b356f06f7eef087caf2ee2fad3c0fc0283a47a770f3bd2ac3f707f3144af62cca13f9343e00f8971192c47f09a57d55b6811489b8109f0ab0d0d37ee6516547014cd0fc5b403e246afebeaaddabb56d0e392e6bac81d75e723c65bbda7b2fff91f538cfb9d97a2478ab3a9ff371db716c389c9fd0bdfe7164053"\n      },\n      "index": 0\n    },\n    {\n      "type": "access",\n      "index": 1,\n      "serviceEndpoint": "https://provider.ropsten.oceanprotocol.com",\n      "attributes": {\n        "main": {\n          "creator": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7",\n          "datePublished": "2020-12-10T09:41:01Z",\n          "cost": "1",\n          "timeout": 0,\n          "name": "dataAssetAccess"\n        }\n      }\n    }\n  ],\n  "dataToken": "0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n  "created": "2020-12-10T09:42:06Z",\n  "proof": {\n    "created": "2020-12-10T09:42:06Z",\n    "creator": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7",\n    "type": "AddressHash",\n    "signatureValue": "0x6184e0f6a704c90afbd37682a28963da55325c66c390a609e313934596f63b43"\n  },\n  "dataTokenInfo": {\n    "name": "Wheedling Penguin Token",\n    "symbol": "WHEPEN-58",\n    "address": "0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n    "cap": 1000\n  }\n}'
2021-03-30 07:28:48,104 - aquarius.events.events_monitor - DEBUG - After unpack rawddo:b'{\n  "@context": "https://w3id.org/did/v1",\n  "id": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n  "publicKey": [\n    {\n      "id": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n      "type": "EthereumECDSAKey",\n      "owner": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7"\n    }\n  ],\n  "authentication": [\n    {\n      "type": "RsaSignatureAuthentication2018",\n      "publicKey": "did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af"\n    }\n  ],\n  "service": [\n    {\n      "type": "metadata",\n      "attributes": {\n        "curation": {\n          "rating": 0,\n          "numVotes": 0\n        },\n        "main": {\n          "type": "dataset",\n          "name": "Maritime Word List",\n          "dateCreated": "2020-12-10T09:41:01Z",\n          "author": "Ocean Team",\n          "license": "https://market.oceanprotocol.com/terms",\n          "files": [\n            {\n              "contentLength": "3215",\n              "contentType": "text/plain",\n              "index": 0\n            }\n          ],\n          "datePublished": "2020-12-10T09:41:01Z"\n        },\n        "additionalInformation": {\n          "description": "The wordlist used by ocean.js to generate datatoken names within the Ocean Protocol ecosystem.\\n\\n### Data Structure\\n\\nThe json object holds 2 arrays of strings, nouns and adjectives.\\n\\n```json\\n{\\n  \\"nouns\\": [ \\"Crab\\", \\"Fish\\", \\"Shark\\"],\\n  \\"adjectives\\": [ \\"adamant\\", \\"adroit\\" ]\\n}\\n```",\n          "tags": [\n            "wordlist",\n            "animals"\n          ],\n          "links": [\n            {\n              "contentLength": "74",\n              "contentType": "text/plain",\n              "url": "https://ipfs.oceanprotocol.com/ipfs/QmWTpf5JXyAEfNyuBHc9Gey6pw4WKx6GfJs5efMSyMGwza"\n            }\n          ],\n          "termsAndConditions": true\n        },\n        "encryptedFiles": "0x04e164b38786f9c2049ca54950e2693b2a6116a09066068c803310635baaf703e757075960fe534db0c4426f3ad736a60576218721ad68e6b98dec9a0cdaa4324a23fd1ab404fdd2b7e2395fa72bd5885c02b78e0b99bbf404e3b2f129010cc1ab97e0a3b11e26b51961aa595a7c90c40a713d8eb856b356f06f7eef087caf2ee2fad3c0fc0283a47a770f3bd2ac3f707f3144af62cca13f9343e00f8971192c47f09a57d55b6811489b8109f0ab0d0d37ee6516547014cd0fc5b403e246afebeaaddabb56d0e392e6bac81d75e723c65bbda7b2fff91f538cfb9d97a2478ab3a9ff371db716c389c9fd0bdfe7164053"\n      },\n      "index": 0\n    },\n    {\n      "type": "access",\n      "index": 1,\n      "serviceEndpoint": "https://provider.ropsten.oceanprotocol.com",\n      "attributes": {\n        "main": {\n          "creator": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7",\n          "datePublished": "2020-12-10T09:41:01Z",\n          "cost": "1",\n          "timeout": 0,\n          "name": "dataAssetAccess"\n        }\n      }\n    }\n  ],\n  "dataToken": "0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n  "created": "2020-12-10T09:42:06Z",\n  "proof": {\n    "created": "2020-12-10T09:42:06Z",\n    "creator": "0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7",\n    "type": "AddressHash",\n    "signatureValue": "0x6184e0f6a704c90afbd37682a28963da55325c66c390a609e313934596f63b43"\n  },\n  "dataTokenInfo": {\n    "name": "Wheedling Penguin Token",\n    "symbol": "WHEPEN-58",\n    "address": "0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af",\n    "cap": 1000\n  }\n}'
2021-03-30 07:28:48,104 - aquarius - INFO - got event MetadataCreated request: {'@context': 'https://w3id.org/did/v1', 'id': 'did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af', 'publicKey': [{'id': 'did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af', 'type': 'EthereumECDSAKey', 'owner': '0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7'}], 'authentication': [{'type': 'RsaSignatureAuthentication2018', 'publicKey': 'did:op:2b6DA6D5f354D893AF9d170E67e74B2F11b843af'}], 'service': [{'type': 'metadata', 'attributes': {'curation': {'rating': 0, 'numVotes': 0}, 'main': {'type': 'dataset', 'name': 'Maritime Word List', 'dateCreated': '2020-12-10T09:41:01Z', 'author': 'Ocean Team', 'license': 'https://market.oceanprotocol.com/terms', 'files': [{'contentLength': '3215', 'contentType': 'text/plain', 'index': 0}], 'datePublished': '2020-12-10T09:41:01Z'}, 'additionalInformation': {'description': 'The wordlist used by ocean.js to generate datatoken names within the Ocean Protocol ecosystem.\n\n### Data Structure\n\nThe json object holds 2 arrays of strings, nouns and adjectives.\n\n```json\n{\n  "nouns": [ "Crab", "Fish", "Shark"],\n  "adjectives": [ "adamant", "adroit" ]\n}\n```', 'tags': ['wordlist', 'animals'], 'links': [{'contentLength': '74', 'contentType': 'text/plain', 'url': 'https://ipfs.oceanprotocol.com/ipfs/QmWTpf5JXyAEfNyuBHc9Gey6pw4WKx6GfJs5efMSyMGwza'}], 'termsAndConditions': True}, 'encryptedFiles': '0x04e164b38786f9c2049ca54950e2693b2a6116a09066068c803310635baaf703e757075960fe534db0c4426f3ad736a60576218721ad68e6b98dec9a0cdaa4324a23fd1ab404fdd2b7e2395fa72bd5885c02b78e0b99bbf404e3b2f129010cc1ab97e0a3b11e26b51961aa595a7c90c40a713d8eb856b356f06f7eef087caf2ee2fad3c0fc0283a47a770f3bd2ac3f707f3144af62cca13f9343e00f8971192c47f09a57d55b6811489b8109f0ab0d0d37ee6516547014cd0fc5b403e246afebeaaddabb56d0e392e6bac81d75e723c65bbda7b2fff91f538cfb9d97a2478ab3a9ff371db716c389c9fd0bdfe7164053'}, 'index': 0}, {'type': 'access', 'index': 1, 'serviceEndpoint': 'https://provider.ropsten.oceanprotocol.com', 'attributes': {'main': {'creator': '0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7', 'datePublished': '2020-12-10T09:41:01Z', 'cost': '1', 'timeout': 0, 'name': 'dataAssetAccess'}}}], 'dataToken': '0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af', 'created': '2020-12-10T09:42:06Z', 'proof': {'created': '2020-12-10T09:42:06Z', 'creator': '0x903322C7E45A60d7c8C3EA236c5beA9Af86310c7', 'type': 'AddressHash', 'signatureValue': '0x6184e0f6a704c90afbd37682a28963da55325c66c390a609e313934596f63b43'}, 'dataTokenInfo': {'name': 'Wheedling Penguin Token', 'symbol': 'WHEPEN-58', 'address': '0x2b6DA6D5f354D893AF9d170E67e74B2F11b843af', 'cap': 1000}}
...........................................................................................................................
```



confirm Aquarius service is accessible on localhost port 5000/tcp

```shell
$ curl localhost:5000
{"plugin":"elasticsearch","software":"Aquarius","version":"2.2.6"}
```

