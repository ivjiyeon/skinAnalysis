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
        build=docker.DockerBuildArgs(
        context="..",
        dockerfile="../Dockerfile",
        # additional properties as needed
    ),
    # Assign a name to the image that includes the Pulumi stack
    image_name=f"gcr.io/face-generation-app:{stack}",
    # Enable pushing to a Docker registry (set skip_push=False)
    skip_push=False,
)

# Create a GKE Cluster
cluster = gcp.container.Cluster("gke-cluster",
    initial_node_count=1,
    node_version="latest",
    min_master_version="latest",
    node_config=gcp.container.ClusterNodeConfigArgs(
        preemptible=True,
        machine_type="e2-micro",
        disk_size_gb=10,
    ),
    project=project,
    location=zone)

# Export the Cluster name
pulumi.export("cluster_name", cluster.name)

# Export the Kubeconfig
kubeconfig = pulumi.Output.all(cluster.name, cluster.endpoint).apply(lambda args: f"""
apiVersion: v1
clusters:
- cluster:
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
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gcloud
      args:
      - container
      - clusters
      - get-credentials
      - {args[0]}
      # The below args are optional; use if you're working with a named configuration or need to specify the auth plugin explicitly
      # - --kubeconfig
      # - /path/to/kubeconfig
      - --project
      - [PROJECT_ID]
      - --zone
      - [COMPUTE_ZONE]
      provideClusterInfo: true
""")

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
pulumi.export('registry_image_tag', image.base_image_name)
# Export the FastAPI service's address
pulumi.export("app_service_ip", app_service.status.apply(lambda status: status.load_balancer.ingress[0].ip))