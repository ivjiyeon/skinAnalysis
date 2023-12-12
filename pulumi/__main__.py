import pulumi
import pulumi_docker as docker
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s

# Configure the Google Cloud provider
config = pulumi.Config("gcp")
project = config.require("project")
zone = config.require("zone")

# A Docker build and push example using a local Dockerfile
stack = pulumi.get_stack()
app_name = f"face-generation-app-{stack}"

# Define a Docker image that is built from a local Dockerfile and pushed to a Docker registry
image = docker.Image(app_name,
    # Specify the path to the directory of the Dockerfile
    build=docker.DockerBuild(context="."),
    # Assign a name to the image that includes the Pulumi stack
    image_name=f"gcr.io/face-generation-app:{stack}",
    # Enable pushing to a Docker registry (set skip_push=False)
    skip_push=False,
)

# Create a GKE Cluster
cluster = gcp.container.Cluster("gke-cluster",
    initial_node_count=3,
    node_version="latest",
    min_master_version="latest",
    node_config=gcp.container.ClusterNodeConfigArgs(
        preemptible=True,
        machine_type="e2-medium",
    ),
    project=project,
    location=zone)

# Export the Cluster name
pulumi.export("cluster_name", cluster.name)

# Export the Kubeconfig
kubeconfig = pulumi.Output.all(cluster.name, cluster.endpoint, cluster.master_auth).apply(
    lambda args: f"""
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {args[2][0].cluster_ca_certificate}
    server: https://{args[1]}
  name: gke_{args[0]}
contexts:
- context:
    cluster: gke_{args[0]}
    user: gke_{args[0]}
  name: gke_{args[0]}
current-context: gke_{args[0]}
kind: Config
preferences: {{}}
users:
- name: gke_{args[0]}
  user:
    auth-provider:
      config:
        cmd-args: config config-helper --format=json
        cmd-path: gcloud
        expiry-key: '{{.credential.token_expiry}}'
        token-key: '{{.credential.access_token}}'
      name: gcp
"""
)

# Export kubeconfig to be used by kubectl
pulumi.export("kubeconfig", kubeconfig)

# Create a provider for the created cluster
k8s_provider = k8s.Provider("gke-k8s",
    kubeconfig=kubeconfig)

# Define the Deployment for the FastAPI app using the container image
app_labels = {"app": app_name}

app_deployment = k8s.apps.v1.Deployment("app-deployment",
    spec=k8s.apps.v1.DeploymentSpecArgs(
        selector=k8s.meta.v1.LabelSelectorArgs(match_labels=app_labels),
        replicas=2,
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(labels=app_labels),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[k8s.core.v1.ContainerArgs(
                    name=app_name,
                    image=f"gcr.io/face-generation-app:{stack}"  # Replace with your image path
                )],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider))

# Define a service to expose the FastAPI app
app_service = k8s.core.v1.Service("app-service",
    spec=k8s.core.v1.ServiceSpecArgs(
        selector=app_labels,
        ports=[k8s.core.v1.ServicePortArgs(
            port=80,
            target_port=8000  # Assuming the FastAPI app listens on port 8000
        )],
        type="LoadBalancer",
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider))

# Export the resulting base name and tag of the image
pulumi.export('base_image_name', image.base_image_name)
pulumi.export('registry_image_name', image.image_name)
pulumi.export('registry_image_tag', image.image_tag)
# Export the FastAPI service's address
pulumi.export("app_service_ip", app_service.status.apply(lambda status: status.load_balancer.ingress[0].ip))