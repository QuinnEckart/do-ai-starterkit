data "digitalocean_project" "selected_proj" {
  count = var.project_uuid != "" ? 1 : 0
  id    = var.project_uuid
}

resource "digitalocean_project_resources" "project_resources" {
  count   = var.project_uuid != "" ? 1 : 0
  project = data.digitalocean_project.selected_proj[0].id
  resources = [
    digitalocean_database_cluster.pg.urn,
    digitalocean_database_cluster.valkey.urn,
    digitalocean_spaces_bucket.bucket.urn,
    digitalocean_app.ai_app.urn,
  ]
}
