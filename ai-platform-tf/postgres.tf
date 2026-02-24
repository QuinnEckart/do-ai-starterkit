resource "digitalocean_database_cluster" "pg" {
  name       = var.pg_cluster_name
  engine     = var._pg_engine
  version    = var._pg_engine_version
  size       = var.pg_size_slug
  region     = var.region
  node_count = var.pg_node_count
  tags       = [for k, v in digitalocean_tag.tags : v.id]
}

resource "digitalocean_database_db" "kb" {
  cluster_id = digitalocean_database_cluster.pg.id
  name       = "kb"
}
