terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # For production, swap to an Azure Storage backend so state is shared and locked.
  # backend "azurerm" { ... }
}

provider "azurerm" {
  features {}
}
