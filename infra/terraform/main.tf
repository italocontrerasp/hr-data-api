locals {
  base_name = "${var.project}-${var.environment}"
  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Suffix to keep globally-unique resource names (ACR, Storage) collision-free.
resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
  numeric = true
}

resource "random_password" "db_admin_password" {
  length           = 24
  special          = true
  override_special = "_-"
}

# -------------------- Resource group --------------------
resource "azurerm_resource_group" "main" {
  name     = "rg-${local.base_name}"
  location = var.location
  tags     = local.tags
}

# -------------------- PostgreSQL Flexible Server --------------------
resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "psql-${local.base_name}-${random_string.suffix.result}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = "16"
  administrator_login           = var.db_admin_login
  administrator_password        = random_password.db_admin_password.result
  sku_name                      = var.db_sku_name
  storage_mb                    = 32768
  backup_retention_days         = 7
  public_network_access_enabled = true
  zone                          = "1"

  tags = local.tags
}

resource "azurerm_postgresql_flexible_server_database" "hr_data" {
  name      = "hr_data"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Allow Azure-internal services (Container Apps) to reach the DB.
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# -------------------- Container Registry --------------------
resource "azurerm_container_registry" "main" {
  name                = "acr${replace(var.project, "-", "")}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = local.tags
}

# -------------------- Storage account for historical CSVs --------------------
resource "azurerm_storage_account" "csv" {
  name                     = "st${replace(var.project, "-", "")}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = local.tags
}

resource "azurerm_storage_container" "historical" {
  name                  = "csv-historical"
  storage_account_name  = azurerm_storage_account.csv.name
  container_access_type = "private"
}

# -------------------- Container Apps Environment --------------------
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.base_name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${local.base_name}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  tags = local.tags
}

# -------------------- Container App (the API) --------------------
resource "azurerm_container_app" "api" {
  name                         = "ca-${local.base_name}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  tags = local.tags

  secret {
    name  = "database-url"
    value = "postgresql+psycopg2://${var.db_admin_login}:${random_password.db_admin_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/hr_data?sslmode=require"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "api"
      image  = var.container_image
      cpu    = var.container_cpu
      memory = var.container_memory

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
