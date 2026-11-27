# SAHYOG Role 1 — Aditya Integration Guide

**For:** Aditya (Role 4: Flutter Android Frontend)  
**Branch:** `Ai/ml-and-monitoring`  
**Commit:** Based on `73cc389` and later updates  

This document provides exact public signatures, import paths, and usage examples for Aditya's Flutter frontend integration with Role 1's AI/ML and Health Monitoring components.

---

## 1. Exact Dart Imports

```dart
// Core domain models
import 'package:sahyog_monitoring/features/monitoring/domain/hr_sample.dart';
import 'package:sahyog_monitoring/features/monitoring/domain/heart_rate_source.dart';
import 'package:sahyog_monitoring/features/monitoring/domain/sim_scenario.dart';
import 'package:sahyog_monitoring/features/monitoring/domain/simulator_heart_rate_source.dart';

// ML / backend response models
import 'package:sahyog_monitoring/core/ml/backend_detection_result.dart';

// Buffer for monitoring UI
import 'package:sahyog_monitoring/core/buffer/last_moments_buffer.dart';