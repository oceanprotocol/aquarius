##
## Copyright 2021 Ocean Protocol Foundation
## SPDX-License-Identifier: Apache-2.0
##
rm -rf $LD_LIBRARY_PATH/python3.8/site-packages/artifacts/
mkdir ${LD_LIBRARY_PATH}/python3.8/site-packages/artifacts/

find ./artifacts -name '*.json' -exec cp -prv '{}' ${LD_LIBRARY_PATH}'/python3.8/site-packages/artifacts/' ';'
