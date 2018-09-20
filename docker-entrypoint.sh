#!/bin/sh

export CONFIG_FILE=/provider/oceandb.ini
envsubst < /provider/oceandb.ini.template > /provider/oceandb.ini
echo "Waiting for contracts to be generated..."
while [ ! -f "/usr/local/keeper-contracts/ready" ]; do
  sleep 2
done
market=$(python -c "import sys, json; print(json.load(open('/usr/local/keeper-contracts/OceanMarket.development.json', 'r'))['address'])")
token=$(python -c "import sys, json; print(json.load(open('/usr/local/keeper-contracts/OceanToken.development.json', 'r'))['address'])")
auth=$(python -c "import sys, json; print(json.load(open('/usr/local/keeper-contracts/OceanAuth.development.json', 'r'))['address'])")
sed -i -e "/token.address =/c token.address = ${token}" /provider/oceandb.ini
sed -i -e "/market.address =/c market.address = ${market}" /provider/oceandb.ini 
sed -i -e "/auth.address =/c auth.address = ${auth}" /provider/oceandb.ini
gunicorn -b ${PROVIDER_HOST}:${PROVIDER_PORT} -w ${PROVICER_WORKERS} provider.run:app
tail -f /dev/null
