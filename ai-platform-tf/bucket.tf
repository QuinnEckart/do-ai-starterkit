resource "digitalocean_spaces_bucket" "bucket" {
  name   = local.bucket_name
  region = var.spaces_region
}
