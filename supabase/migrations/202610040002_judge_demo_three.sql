-- Safe additive upgrade: preserves the activated demo account, records and review history.
begin;
create table if not exists public.sonar_judge_demo_examples (analysis_id text primary key, name text not null, analysis jsonb not null, image_sha256 text not null, image_bytes integer not null);
alter table public.sonar_judge_demo_examples enable row level security;
revoke all on public.sonar_judge_demo_examples from public,anon,authenticated;
insert into public.sonar_judge_demo_examples values('ANL-1c7ed9ac','Contact 103',$fixture${
  "schema_version": "F8.0",
  "analysis_id": "ANL-1c7ed9ac",
  "status": "COMPLETED",
  "input": {
    "input_id": "IMG-cc4234c3",
    "filename": "Contact_103_sslo_png_jpg.rf.53fe66a3739b5f18e390901f89cf481e.jpg",
    "sha256": "94976a1512bff544b94954335b3cf9ad988e9377cf4dc31fa4b8d6e1373dbed3",
    "width": 640,
    "height": 640
  },
  "summary": {
    "candidate_count": 1,
    "confirmed_count": 0,
    "review_count": 1,
    "rejected_count": 0,
    "unknown_count": 0
  },
  "candidates": [
    {
      "schema_version": "F7.0",
      "candidate_id": "CAND-4ae62fad",
      "detection": {
        "class_id": 0,
        "class_name": "Crab Pot",
        "confidence": 0.30360063910484314,
        "bbox": [
          428.972412109375,
          302.0389709472656,
          443.04762268066406,
          316.0032043457031
        ],
        "source_mode": "TILED"
      },
      "classification": {
        "class_id": 0,
        "class_name": "Crab Pot",
        "reliability": {
          "estimated_tp_rate": 0.85,
          "support_count": 100,
          "method": "CLASS_CONDITIONAL_EMPIRICAL_BINNING",
          "source_split": "CALIB",
          "confidence_interval": null
        },
        "presentation": {
          "reliability_band": "MODERATE",
          "uncertainty_level": "LOW_UNCERTAINTY"
        }
      },
      "decision": {
        "status": "REVIEW",
        "fusion_score": 0.6945826116971042,
        "reason_codes": [
          "MODERATE_FUSION_EVIDENCE",
          "NO_SHADOW_SUPPORT"
        ]
      },
      "evidence": {
        "ai_confidence": 0.30360063910484314,
        "bbox": [
          428.972412109375,
          302.0389709472656,
          443.04762268066406,
          316.0032043457031
        ],
        "geometry": {
          "width_px": 14.075210571289062,
          "height_px": 13.9642333984375,
          "bbox_area_px": 196.5495255496353,
          "aspect_ratio": 1.007947244197736
        },
        "seabed": {
          "background_mean": 113.74746376811594,
          "background_std": 19.033713246351574,
          "local_contrast": 0.05086093430294398
        },
        "shadow": {
          "shadow_candidate_presence": 0.344061850475435,
          "shadow_area_px": 149.7520194663888,
          "area_ratio": 0.7619047619047619,
          "adjacency": 1.0,
          "mean_intensity_ratio": 0.5484188212509915
        },
        "quality": {
          "boundary_strength": 0.1620314065044534,
          "artifact_flags": {
            "near_image_edge": false,
            "near_nadir": false,
            "dropout": false,
            "extreme_saturation": false,
            "very_low_dynamic_range": false
          }
        }
      },
      "localization": {
        "metadata": {
          "status": "PIXEL_ONLY",
          "available_spaces": [
            "IMAGE_PIXEL"
          ],
          "unavailable_spaces": [
            "SONAR_RELATIVE",
            "GEOGRAPHIC"
          ],
          "reason_code": "NO_SONAR_NAV_METADATA"
        },
        "pixel_convention": {
          "origin": "top-left",
          "axes": "x rightward, y downward",
          "indexing": "zero-based continuous",
          "bounding_box_semantics": "[x_min, y_min, x_max, y_max), max exclusive",
          "reference": "pixel center of (i,j) is (j + 0.5, i + 0.5)"
        },
        "image_geometry": null,
        "coordinate_provenance": [],
        "coordinates": {
          "image": {
            "coordinate_system": "IMAGE_PIXEL",
            "x_min": 428.972412109375,
            "y_min": 302.0389709472656,
            "x_max": 443.04762268066406,
            "y_max": 316.0032043457031,
            "center_x": 436.01001739501953,
            "center_y": 309.0210876464844,
            "width_px": 14.075210571289062,
            "height_px": 13.9642333984375
          },
          "normalized_image": null,
          "sonar": null,
          "geographic": null
        }
      },
      "localization_uncertainty": {
        "validation_reference": {
          "scope": "CLASS_LEVEL",
          "class_name": "Crab Pot",
          "median_center_error_px": 75.5,
          "p90_center_error_px": 130.2,
          "median_normalized_center_error": 0.11,
          "p90_normalized_center_error": 0.19
        },
        "error_envelope": {
          "status": "CLASS_CONDITIONAL_ESTIMATE",
          "scope": "CLASS_CONDITIONAL",
          "method": "CALIB_DERIVED_P90_ENVELOPE",
          "envelope_px": 130.2,
          "envelope_normalized": 0.19,
          "reason": "CALIB derived bounds"
        }
      },
      "quality": {
        "image": {
          "flags": []
        },
        "detection": {
          "flags": []
        },
        "evidence": {
          "completeness": {
            "available": [],
            "missing": []
          },
          "flags": []
        },
        "localization": {
          "flags": []
        },
        "metadata": {
          "flags": []
        }
      },
      "provenance": {
        "candidate_id": "CAND-4ae62fad",
        "input_id": "IMG-cc4234c3",
        "source_dataset": "drishti_sss_v3",
        "source_dataset_version": null,
        "image_sha256": "94976a1512bff544b94954335b3cf9ad988e9377cf4dc31fa4b8d6e1373dbed3",
        "pipeline_version": "v1.2",
        "detector_version": "V6-P2",
        "fusion_version": "D2-v1",
        "decision_policy_version": "E1-v1",
        "calibration_version": "F5-v1.0",
        "preprocessing_version": "v1.0",
        "coordinate_contract_version": "F3-v1.0",
        "detector_artifact_sha256": "detector_hash",
        "fusion_artifact_sha256": "fusion_hash",
        "decision_policy_sha256": "policy_hash",
        "classification_calibration_sha256": "calib_hash",
        "localization_uncertainty_sha256": "loc_hash",
        "processing_timestamp": "2026-09-30T06:51:07.068475+00:00",
        "runtime_version": "python3"
      }
    }
  ],
  "artifacts": {
    "visual_audit_url": null,
    "report_url": null
  },
  "processing": {
    "status": "COMPLETED",
    "pipeline_version": "v1.2",
    "processing_time_ms": 2500
  }
}$fixture$::jsonb,'94976a1512bff544b94954335b3cf9ad988e9377cf4dc31fa4b8d6e1373dbed3',70662) on conflict(analysis_id) do update set name=excluded.name,analysis=excluded.analysis,image_sha256=excluded.image_sha256,image_bytes=excluded.image_bytes;
insert into public.sonar_judge_demo_examples values('ANL-8ae35627','Contact 104',$fixture${
  "schema_version": "F8.0",
  "analysis_id": "ANL-8ae35627",
  "status": "COMPLETED",
  "input": {
    "input_id": "IMG-4afcbcb1",
    "filename": "Contact_104_sslo_png_jpg.rf.22e4adfcabfab6cc53f6c4ec51d4099d.jpg",
    "sha256": "a166e38c7cf6bea3f0421b034728b7d0a722dc093f56f69ff6f5d193388eddb0",
    "width": 640,
    "height": 640
  },
  "summary": {
    "candidate_count": 1,
    "confirmed_count": 0,
    "review_count": 1,
    "rejected_count": 0,
    "unknown_count": 0
  },
  "candidates": [
    {
      "schema_version": "F7.0",
      "candidate_id": "CAND-7f896856",
      "detection": {
        "class_id": 0,
        "class_name": "Crab Pot",
        "confidence": 0.48715871572494507,
        "bbox": [
          313.6850109100342,
          313.83905029296875,
          327.2974662780762,
          327.63897705078125
        ],
        "source_mode": "TILED"
      },
      "classification": {
        "class_id": 0,
        "class_name": "Crab Pot",
        "reliability": {
          "estimated_tp_rate": 0.85,
          "support_count": 100,
          "method": "CLASS_CONDITIONAL_EMPIRICAL_BINNING",
          "source_split": "CALIB",
          "confidence_interval": null
        },
        "presentation": {
          "reliability_band": "MODERATE",
          "uncertainty_level": "LOW_UNCERTAINTY"
        }
      },
      "decision": {
        "status": "REVIEW",
        "fusion_score": 0.7509558051036817,
        "reason_codes": [
          "MODERATE_FUSION_EVIDENCE",
          "NO_SHADOW_SUPPORT"
        ]
      },
      "evidence": {
        "ai_confidence": 0.48715871572494507,
        "bbox": [
          313.6850109100342,
          313.83905029296875,
          327.2974662780762,
          327.63897705078125
        ],
        "geometry": {
          "width_px": 13.612455368041992,
          "height_px": 13.7999267578125,
          "bbox_area_px": 187.8508870729711,
          "aspect_ratio": 0.9864150445824377
        },
        "seabed": {
          "background_mean": 113.53051470588235,
          "background_std": 17.52806014315722,
          "local_contrast": 0.048816364257952494
        },
        "shadow": {
          "shadow_candidate_presence": 0.2803311468002721,
          "shadow_area_px": 143.76343398441665,
          "area_ratio": 0.7653061224489796,
          "adjacency": 0.8571428571428572,
          "mean_intensity_ratio": 0.5726507406555852
        },
        "quality": {
          "boundary_strength": 0.15536400633456207,
          "artifact_flags": {
            "near_image_edge": false,
            "near_nadir": false,
            "dropout": false,
            "extreme_saturation": false,
            "very_low_dynamic_range": false
          }
        }
      },
      "localization": {
        "metadata": {
          "status": "PIXEL_ONLY",
          "available_spaces": [
            "IMAGE_PIXEL"
          ],
          "unavailable_spaces": [
            "SONAR_RELATIVE",
            "GEOGRAPHIC"
          ],
          "reason_code": "NO_SONAR_NAV_METADATA"
        },
        "pixel_convention": {
          "origin": "top-left",
          "axes": "x rightward, y downward",
          "indexing": "zero-based continuous",
          "bounding_box_semantics": "[x_min, y_min, x_max, y_max), max exclusive",
          "reference": "pixel center of (i,j) is (j + 0.5, i + 0.5)"
        },
        "image_geometry": null,
        "coordinate_provenance": [],
        "coordinates": {
          "image": {
            "coordinate_system": "IMAGE_PIXEL",
            "x_min": 313.6850109100342,
            "y_min": 313.83905029296875,
            "x_max": 327.2974662780762,
            "y_max": 327.63897705078125,
            "center_x": 320.4912385940552,
            "center_y": 320.739013671875,
            "width_px": 13.612455368041992,
            "height_px": 13.7999267578125
          },
          "normalized_image": null,
          "sonar": null,
          "geographic": null
        }
      },
      "localization_uncertainty": {
        "validation_reference": {
          "scope": "CLASS_LEVEL",
          "class_name": "Crab Pot",
          "median_center_error_px": 75.5,
          "p90_center_error_px": 130.2,
          "median_normalized_center_error": 0.11,
          "p90_normalized_center_error": 0.19
        },
        "error_envelope": {
          "status": "CLASS_CONDITIONAL_ESTIMATE",
          "scope": "CLASS_CONDITIONAL",
          "method": "CALIB_DERIVED_P90_ENVELOPE",
          "envelope_px": 130.2,
          "envelope_normalized": 0.19,
          "reason": "CALIB derived bounds"
        }
      },
      "quality": {
        "image": {
          "flags": []
        },
        "detection": {
          "flags": []
        },
        "evidence": {
          "completeness": {
            "available": [],
            "missing": []
          },
          "flags": []
        },
        "localization": {
          "flags": []
        },
        "metadata": {
          "flags": []
        }
      },
      "provenance": {
        "candidate_id": "CAND-7f896856",
        "input_id": "IMG-4afcbcb1",
        "source_dataset": "drishti_sss_v3",
        "source_dataset_version": null,
        "image_sha256": "a166e38c7cf6bea3f0421b034728b7d0a722dc093f56f69ff6f5d193388eddb0",
        "pipeline_version": "v1.2",
        "detector_version": "V6-P2",
        "fusion_version": "D2-v1",
        "decision_policy_version": "E1-v1",
        "calibration_version": "F5-v1.0",
        "preprocessing_version": "v1.0",
        "coordinate_contract_version": "F3-v1.0",
        "detector_artifact_sha256": "detector_hash",
        "fusion_artifact_sha256": "fusion_hash",
        "decision_policy_sha256": "policy_hash",
        "classification_calibration_sha256": "calib_hash",
        "localization_uncertainty_sha256": "loc_hash",
        "processing_timestamp": "2026-09-30T06:51:07.180193+00:00",
        "runtime_version": "python3"
      }
    }
  ],
  "artifacts": {
    "visual_audit_url": null,
    "report_url": null
  },
  "processing": {
    "status": "COMPLETED",
    "pipeline_version": "v1.2",
    "processing_time_ms": 2500
  }
}$fixture$::jsonb,'a166e38c7cf6bea3f0421b034728b7d0a722dc093f56f69ff6f5d193388eddb0',71783) on conflict(analysis_id) do update set name=excluded.name,analysis=excluded.analysis,image_sha256=excluded.image_sha256,image_bytes=excluded.image_bytes;
insert into public.sonar_judge_demo_examples values('ANL-600a600b','Contact 105',$fixture${
  "schema_version": "F8.0",
  "analysis_id": "ANL-600a600b",
  "status": "COMPLETED",
  "input": {
    "input_id": "IMG-e8b99d1d",
    "filename": "Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg",
    "sha256": "6407b4344f90aa1ade206d83c2e9072e6a007c200f3a721212258908225e29e3",
    "width": 640,
    "height": 640
  },
  "summary": {
    "candidate_count": 2,
    "confirmed_count": 0,
    "review_count": 2,
    "rejected_count": 0,
    "unknown_count": 0
  },
  "candidates": [
    {
      "schema_version": "F7.0",
      "candidate_id": "CAND-3a45c97a",
      "detection": {
        "class_id": 0,
        "class_name": "Crab Pot",
        "confidence": 0.24502891302108765,
        "bbox": [
          328.72943115234375,
          9.503705978393555,
          343.97467041015625,
          21.56841468811035
        ],
        "source_mode": "GLOBAL"
      },
      "classification": {
        "class_id": 0,
        "class_name": "Crab Pot",
        "reliability": {
          "estimated_tp_rate": 0.85,
          "support_count": 100,
          "method": "CLASS_CONDITIONAL_EMPIRICAL_BINNING",
          "source_split": "CALIB",
          "confidence_interval": null
        },
        "presentation": {
          "reliability_band": "MODERATE",
          "uncertainty_level": "LOW_UNCERTAINTY"
        }
      },
      "decision": {
        "status": "REVIEW",
        "fusion_score": 0.7802626607365318,
        "reason_codes": [
          "MODERATE_FUSION_EVIDENCE",
          "NO_SHADOW_SUPPORT"
        ]
      },
      "evidence": {
        "ai_confidence": 0.24502891302108765,
        "bbox": [
          328.72943115234375,
          9.503705978393555,
          343.97467041015625,
          21.56841468811035
        ],
        "geometry": {
          "width_px": 15.2452392578125,
          "height_px": 12.064708709716797,
          "bbox_area_px": 183.9293708554469,
          "aspect_ratio": 1.2636226555170897
        },
        "seabed": {
          "background_mean": 78.2722891566265,
          "background_std": 14.164662574311443,
          "local_contrast": 0.08976925639596614
        },
        "shadow": {
          "shadow_candidate_presence": 0.27439330594493566,
          "shadow_area_px": 218.67158535036467,
          "area_ratio": 1.1888888888888889,
          "adjacency": 0.6,
          "mean_intensity_ratio": 0.5426778234251072
        },
        "quality": {
          "boundary_strength": 0.2573789426982401,
          "artifact_flags": {
            "near_image_edge": true,
            "near_nadir": false,
            "dropout": false,
            "extreme_saturation": false,
            "very_low_dynamic_range": false
          }
        }
      },
      "localization": {
        "metadata": {
          "status": "PIXEL_ONLY",
          "available_spaces": [
            "IMAGE_PIXEL"
          ],
          "unavailable_spaces": [
            "SONAR_RELATIVE",
            "GEOGRAPHIC"
          ],
          "reason_code": "NO_SONAR_NAV_METADATA"
        },
        "pixel_convention": {
          "origin": "top-left",
          "axes": "x rightward, y downward",
          "indexing": "zero-based continuous",
          "bounding_box_semantics": "[x_min, y_min, x_max, y_max), max exclusive",
          "reference": "pixel center of (i,j) is (j + 0.5, i + 0.5)"
        },
        "image_geometry": null,
        "coordinate_provenance": [],
        "coordinates": {
          "image": {
            "coordinate_system": "IMAGE_PIXEL",
            "x_min": 328.72943115234375,
            "y_min": 9.503705978393555,
            "x_max": 343.97467041015625,
            "y_max": 21.56841468811035,
            "center_x": 336.35205078125,
            "center_y": 15.536060333251953,
            "width_px": 15.2452392578125,
            "height_px": 12.064708709716797
          },
          "normalized_image": null,
          "sonar": null,
          "geographic": null
        }
      },
      "localization_uncertainty": {
        "validation_reference": {
          "scope": "CLASS_LEVEL",
          "class_name": "Crab Pot",
          "median_center_error_px": 75.5,
          "p90_center_error_px": 130.2,
          "median_normalized_center_error": 0.11,
          "p90_normalized_center_error": 0.19
        },
        "error_envelope": {
          "status": "CLASS_CONDITIONAL_ESTIMATE",
          "scope": "CLASS_CONDITIONAL",
          "method": "CALIB_DERIVED_P90_ENVELOPE",
          "envelope_px": 130.2,
          "envelope_normalized": 0.19,
          "reason": "CALIB derived bounds"
        }
      },
      "quality": {
        "image": {
          "flags": []
        },
        "detection": {
          "flags": []
        },
        "evidence": {
          "completeness": {
            "available": [],
            "missing": []
          },
          "flags": []
        },
        "localization": {
          "flags": []
        },
        "metadata": {
          "flags": []
        }
      },
      "provenance": {
        "candidate_id": "CAND-3a45c97a",
        "input_id": "IMG-e8b99d1d",
        "source_dataset": "drishti_sss_v3",
        "source_dataset_version": null,
        "image_sha256": "6407b4344f90aa1ade206d83c2e9072e6a007c200f3a721212258908225e29e3",
        "pipeline_version": "v1.2",
        "detector_version": "V6-P2",
        "fusion_version": "D2-v1",
        "decision_policy_version": "E1-v1",
        "calibration_version": "F5-v1.0",
        "preprocessing_version": "v1.0",
        "coordinate_contract_version": "F3-v1.0",
        "detector_artifact_sha256": "detector_hash",
        "fusion_artifact_sha256": "fusion_hash",
        "decision_policy_sha256": "policy_hash",
        "classification_calibration_sha256": "calib_hash",
        "localization_uncertainty_sha256": "loc_hash",
        "processing_timestamp": "2026-09-30T06:51:07.295256+00:00",
        "runtime_version": "python3"
      }
    },
    {
      "schema_version": "F7.0",
      "candidate_id": "CAND-88483f73",
      "detection": {
        "class_id": 0,
        "class_name": "Crab Pot",
        "confidence": 0.3225660026073456,
        "bbox": [
          264.5705261230469,
          419.5577392578125,
          279.11651611328125,
          433.9484100341797
        ],
        "source_mode": "TILED"
      },
      "classification": {
        "class_id": 0,
        "class_name": "Crab Pot",
        "reliability": {
          "estimated_tp_rate": 0.85,
          "support_count": 100,
          "method": "CLASS_CONDITIONAL_EMPIRICAL_BINNING",
          "source_split": "CALIB",
          "confidence_interval": null
        },
        "presentation": {
          "reliability_band": "MODERATE",
          "uncertainty_level": "LOW_UNCERTAINTY"
        }
      },
      "decision": {
        "status": "REVIEW",
        "fusion_score": 0.7079501457334088,
        "reason_codes": [
          "MODERATE_FUSION_EVIDENCE",
          "NO_SHADOW_SUPPORT"
        ]
      },
      "evidence": {
        "ai_confidence": 0.3225660026073456,
        "bbox": [
          264.5705261230469,
          419.5577392578125,
          279.11651611328125,
          433.9484100341797
        ],
        "geometry": {
          "width_px": 14.545989990234375,
          "height_px": 14.390670776367188,
          "bbox_area_px": 209.32655306579545,
          "aspect_ratio": 1.0107930489329418
        },
        "seabed": {
          "background_mean": 113.60434782608695,
          "background_std": 17.69866477222496,
          "local_contrast": 0.047227202285089184
        },
        "shadow": {
          "shadow_candidate_presence": 0.30658855604701213,
          "shadow_area_px": 150.5157595854053,
          "area_ratio": 0.719047619047619,
          "adjacency": 1.0,
          "mean_intensity_ratio": 0.5736185644379301
        },
        "quality": {
          "boundary_strength": 0.16347160658839166,
          "artifact_flags": {
            "near_image_edge": false,
            "near_nadir": false,
            "dropout": false,
            "extreme_saturation": false,
            "very_low_dynamic_range": false
          }
        }
      },
      "localization": {
        "metadata": {
          "status": "PIXEL_ONLY",
          "available_spaces": [
            "IMAGE_PIXEL"
          ],
          "unavailable_spaces": [
            "SONAR_RELATIVE",
            "GEOGRAPHIC"
          ],
          "reason_code": "NO_SONAR_NAV_METADATA"
        },
        "pixel_convention": {
          "origin": "top-left",
          "axes": "x rightward, y downward",
          "indexing": "zero-based continuous",
          "bounding_box_semantics": "[x_min, y_min, x_max, y_max), max exclusive",
          "reference": "pixel center of (i,j) is (j + 0.5, i + 0.5)"
        },
        "image_geometry": null,
        "coordinate_provenance": [],
        "coordinates": {
          "image": {
            "coordinate_system": "IMAGE_PIXEL",
            "x_min": 264.5705261230469,
            "y_min": 419.5577392578125,
            "x_max": 279.11651611328125,
            "y_max": 433.9484100341797,
            "center_x": 271.84352111816406,
            "center_y": 426.7530746459961,
            "width_px": 14.545989990234375,
            "height_px": 14.390670776367188
          },
          "normalized_image": null,
          "sonar": null,
          "geographic": null
        }
      },
      "localization_uncertainty": {
        "validation_reference": {
          "scope": "CLASS_LEVEL",
          "class_name": "Crab Pot",
          "median_center_error_px": 75.5,
          "p90_center_error_px": 130.2,
          "median_normalized_center_error": 0.11,
          "p90_normalized_center_error": 0.19
        },
        "error_envelope": {
          "status": "CLASS_CONDITIONAL_ESTIMATE",
          "scope": "CLASS_CONDITIONAL",
          "method": "CALIB_DERIVED_P90_ENVELOPE",
          "envelope_px": 130.2,
          "envelope_normalized": 0.19,
          "reason": "CALIB derived bounds"
        }
      },
      "quality": {
        "image": {
          "flags": []
        },
        "detection": {
          "flags": []
        },
        "evidence": {
          "completeness": {
            "available": [],
            "missing": []
          },
          "flags": []
        },
        "localization": {
          "flags": []
        },
        "metadata": {
          "flags": []
        }
      },
      "provenance": {
        "candidate_id": "CAND-88483f73",
        "input_id": "IMG-e8b99d1d",
        "source_dataset": "drishti_sss_v3",
        "source_dataset_version": null,
        "image_sha256": "6407b4344f90aa1ade206d83c2e9072e6a007c200f3a721212258908225e29e3",
        "pipeline_version": "v1.2",
        "detector_version": "V6-P2",
        "fusion_version": "D2-v1",
        "decision_policy_version": "E1-v1",
        "calibration_version": "F5-v1.0",
        "preprocessing_version": "v1.0",
        "coordinate_contract_version": "F3-v1.0",
        "detector_artifact_sha256": "detector_hash",
        "fusion_artifact_sha256": "fusion_hash",
        "decision_policy_sha256": "policy_hash",
        "classification_calibration_sha256": "calib_hash",
        "localization_uncertainty_sha256": "loc_hash",
        "processing_timestamp": "2026-09-30T06:51:07.297238+00:00",
        "runtime_version": "python3"
      }
    }
  ],
  "artifacts": {
    "visual_audit_url": null,
    "report_url": null
  },
  "processing": {
    "status": "COMPLETED",
    "pipeline_version": "v1.2",
    "processing_time_ms": 2500
  }
}$fixture$::jsonb,'6407b4344f90aa1ade206d83c2e9072e6a007c200f3a721212258908225e29e3',66818) on conflict(analysis_id) do update set name=excluded.name,analysis=excluded.analysis,image_sha256=excluded.image_sha256,image_bytes=excluded.image_bytes;
create or replace function public.sonar_judge_demo_guard() returns trigger
language plpgsql security definer set search_path='' as $$
declare d public.sonar_judge_demo;actor uuid:=auth.uid();
begin
 select * into d from public.sonar_judge_demo where id=true;
 if actor is distinct from d.user_id or actor is null then
  if TG_OP='DELETE' then return OLD;else return NEW;end if;
 end if;
 if not d.enabled then raise exception 'Judge sandbox disabled.' using errcode='42501';end if;
 if TG_TABLE_NAME='sonar_team_members' then
  raise exception 'Judge sandbox cannot join private teams.' using errcode='42501';
 elsif TG_TABLE_NAME='sonar_records' then
  if TG_OP<>'INSERT' then raise exception 'Judge sample cannot be changed or deleted.' using errcode='42501';end if;
  if NEW.owner<>actor or NEW.team_id is not null or NEW.source<>'PRECOMPUTED_EXAMPLE'
     or not exists(select 1 from public.sonar_judge_demo_examples e where e.analysis=NEW.analysis and e.image_sha256=NEW.image_sha256 and e.image_bytes=NEW.image_bytes)
     or NEW.image_mime<>'image/jpeg' or NEW.deleting
     or (select count(*) from public.sonar_records where owner=actor)>=3 then
    raise exception 'Judge sandbox only supports bundled Contacts 103, 104 and 105.' using errcode='42501';
  end if;
 elsif TG_TABLE_NAME='sonar_reviews' then
  if TG_OP<>'INSERT' or NEW.reviewer<>actor or length(NEW.note)>2000
     or not exists(select 1 from public.sonar_records r where r.id=NEW.record_id and r.owner=actor and r.team_id is null)
     then raise exception 'Invalid judge sandbox review.' using errcode='42501';end if;
 end if;
 return NEW;
end $$;
revoke all on function public.sonar_judge_demo_guard() from public,anon,authenticated;

create or replace function public.sonar_judge_demo_catalog_ready() returns boolean language sql stable security definer set search_path='' as $$ select public.sonar_judge_demo_ready() and (select count(*)=3 from public.sonar_judge_demo_examples); $$;
revoke all on function public.sonar_judge_demo_catalog_ready() from public;
grant execute on function public.sonar_judge_demo_catalog_ready() to anon,authenticated;
commit;
