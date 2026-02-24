resource "digitalocean_uptime_check" "app" {
  count = var.enable_uptime_alert ? 1 : 0

  name    = "${var.stack_name}-uptime"
  type    = "https"
  target  = digitalocean_app.ai_app.live_url
  regions = ["us_east", "us_west", "eu_west"]
}

resource "digitalocean_uptime_alert" "app" {
  count = var.enable_uptime_alert && var.alert_email != "" ? 1 : 0

  name      = "${var.stack_name}-uptime-alert"
  check_id  = digitalocean_uptime_check.app[0].id
  type      = "down"
  threshold = 2
  period    = "2m"

  notifications {
    email = [var.alert_email]
  }
}
