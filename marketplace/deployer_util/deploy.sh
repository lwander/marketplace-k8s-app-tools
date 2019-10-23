#!/bin/bash
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -eox pipefail

# This is the entry point for the production deployment

# If any command returns with non-zero exit code, set -e will cause the script
# to exit. Prior to exit, set App assembly status to "Failed".
handle_failure() {
  code=$?
  if [[ -z "$NAME" ]] || [[ -z "$NAMESPACE" ]]; then
    # /bin/expand_config.py might have failed.
    # We fall back to the unexpanded params to get the name and namespace.
    NAME="$(/bin/print_config.py \
            --xtype NAME \
            --values_mode raw)"
    NAMESPACE="$(/bin/print_config.py \
            --xtype NAMESPACE \
            --values_mode raw)"
    export NAME
    export NAMESPACE
  fi
  patch_assembly_phase.sh --status="Failed"
  exit $code
}
trap "handle_failure" EXIT

NAME="$(/bin/print_config.py \
    --xtype NAME \
    --values_mode raw)"
NAMESPACE="$(/bin/print_config.py \
    --xtype NAMESPACE \
    --values_mode raw)"
export NAME
export NAMESPACE

echo "Deploying application \"$NAME\""

app_uid=$(kubectl get "applications.app.k8s.io/$NAME" \
  --namespace="$NAMESPACE" \
  --output=jsonpath='{.metadata.uid}')
app_api_version=$(kubectl get "applications.app.k8s.io/$NAME" \
  --namespace="$NAMESPACE" \
  --output=jsonpath='{.apiVersion}')

/bin/expand_config.py --values_mode raw --app_uid "$app_uid"

create_manifests.sh

# Assign owner references for the resources.
/bin/set_ownership.py \
  --app_name "$NAME" \
  --app_uid "$app_uid" \
  --app_api_version "$app_api_version" \
  --manifests "/data/manifest-expanded" \
  --dest "/data/resources.yaml"

# Kubeflow hack: Remove the owner reference on cluster-scoped IAM resources.
if [[ $(kubectl auth can-i get,update clusterroles | grep 'yes' -c) ]]; then
  deployer_clusterroles=($(kubectl get clusterroles \
    -l 'app.kubernetes.io/name'="$NAME" \
    --output=custom-columns=NAME:.metadata.name \
    | sed -n '1!p')) # removes the column header, which we have to print
  echo $deployer_clusterroles \
    | xargs -n1 -I{} kubectl patch clusterrole {} -p \
    '{"metadata": {"ownerReferences": null}}'
fi
if [[ $(kubectl auth can-i get,update clusterrolebindings | \
      grep 'yes' -c) ]];then
  deployer_clusterrolebindings=($(kubectl get clusterrolebindings \
    -l 'app.kubernetes.io/name'="$NAME" \
    --output=custom-columns=NAME:.metadata.name \
    | sed -n '1!p'))
  echo $deployer_clusterrolebindings \
    | xargs -n1 -I{} kubectl patch clusterrolebinding {} -p \
    '{"metadata": {"ownerReferences": null}}'
fi

# Ensure assembly phase is "Pending", until successful kubectl apply.
/bin/setassemblyphase.py \
  --manifest "/data/resources.yaml" \
  --status "Pending"

# Apply the manifest.
kubectl apply --namespace="$NAMESPACE" --filename="/data/resources.yaml"

patch_assembly_phase.sh --status="Success"

clean_iam_resources.sh

trap - EXIT
