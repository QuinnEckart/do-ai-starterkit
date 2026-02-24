output "app_id" {
  description = "ID of the created App Platform app."
  value       = digitalocean_app.ai_app.id
}

output "app_live_url" {
  description = "Live URL for the deployed app."
  value       = digitalocean_app.ai_app.live_url
}

output "postgres_cluster_id" {
  description = "ID of the created PostgreSQL cluster."
  value       = digitalocean_database_cluster.pg.id
}

output "valkey_cluster_id" {
  description = "ID of the created Valkey cluster."
  value       = digitalocean_database_cluster.valkey.id
}

output "spaces_bucket_id" {
  description = "ID of the created Spaces bucket."
  value       = digitalocean_spaces_bucket.bucket.id
}

output "postgres_host" {
  description = "PostgreSQL cluster host."
  value       = digitalocean_database_cluster.pg.host
}

output "valkey_host" {
  description = "Valkey cluster host."
  value       = digitalocean_database_cluster.valkey.host
}
