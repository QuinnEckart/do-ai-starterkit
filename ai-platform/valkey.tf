resource "digitalocean_database_cluster" "valkey" {
  name       = var.valkey_cluster_name
  engine     = var._valkey_engine
  version    = var._valkey_engine_version
  size       = var.valkey_size_slug
  region     = var.region
  node_count = var.valkey_node_count
  tags       = [for k, v in digitalocean_tag.tags : v.id]
}
