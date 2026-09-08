# ADR 0002 — External Provider Adapters

## Decision

External LLM, notification, object-storage and export dependencies must be accessed through application interfaces.

## Why

BoQPro should not make the core domain dependent on one vendor.

This is especially important for LLM parsing, where provider behavior and pricing can change.

## Required interfaces

- LLMProvider
- NotificationProvider
- ObjectStorageProvider
- ExportRenderer

Implement local/test adapters where practical.
