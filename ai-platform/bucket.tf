resource "digitalocean_spaces_bucket" "bucket" {
  name   = var.spaces_bucket_name
  region = var.spaces_region
}
