#  Copyright 2023 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

es_mapping = """
{
  "settings": {
    "analysis": {
      "normalizer": {
        "ocean_normalizer": {
          "type": "custom",
          "char_filter": [],
          "filter": [
            "lowercase",
            "asciifolding"
          ]
        }
      }
    }
  },
  "mappings": {
    "_queue": {
      "properties": {
        "number_retries": {"type": "integer"},
        "next_retry": {"type": "integer"},
      }
    },
    "_doc": {
      "properties": {
        "@context": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "chainId": {
          "type": "integer",
          "fields": {
            "keyword": {
              "type": "keyword",
            }
          }
        },
        "version": {
          "type": "keyword",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "nftAddress": {
          "type": "keyword",
        },
        "nft": {
          "properties": {
            "address": {
              "type": "keyword"
            },
            "name": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256,
                  "normalizer": "ocean_normalizer"
                }
              }
            },
            "symbol": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256,
                  "normalizer": "ocean_normalizer"
                }
              }
            },
            "tokenURI": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256,
                  "normalizer": "ocean_normalizer"
                }
              }
            },
            "owner": {"type": "text"},
            "state": {
              "type": "integer",
              "fields": {
                "keyword": {
                  "type": "keyword"
                }
              }
            },
            "created": {
              "type": "date"
            },
          }
        },
        "datatokens": {
          "properties": {
            "address": {
              "type": "keyword"
            },
            "name": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256,
                  "normalizer": "ocean_normalizer"
                }
              }
            },
            "symbol": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256,
                  "normalizer": "ocean_normalizer"
                }
              }
            },
            "serviceId": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256,
                }
              }
            },
          }
        },
        "price": {
          "properties": {
            "value": {
              "type": "double",
              "fields": {
                "keyword": {
                  "type": "keyword"
                }
              }
            },
            "tokenAddress": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword"
                }
              }
            },
            "tokenSymbol": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword"
                }
              }
            }
          }
        },
        "authentication": {
          "properties": {
            "publicKey": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "type": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            }
          }
        },
        "created": {
          "type": "date"
        },
        "updated": {
          "type": "date"
        },
        "datatoken": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "id": {
          "type": "keyword",
          "normalizer": "ocean_normalizer"
        },
        "proof": {
          "properties": {
            "created": {
              "type": "date"
            },
            "creator": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "signatureValue": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "type": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            }
          }
        },
        "publicKey": {
          "properties": {
            "id": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "owner": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "publicKeyBase58": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "publicKeyPem": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "type": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            }
          }
        },
        "metadata": {
            "properties": {
                "description": {"type": "text"},
                "copyrightHolder": {"type": "text"},
                "name": {"type": "text"},
                "type": {"type": "text"},
                "author": {"type": "text"},
                "license": {"type": "text"},
                "links": {"type": "text"},
                "tags": {"type": "text"},
                "categories": {"type": "text"},
                "contentLanguage": {"type": "text"},
                "algorithm": {
                    "properties": {
                      "version": {"type": "text"},
                      "language": {"type": "text"},
                      "container": {
                        "properties": {
                          "entrypoint": {"type": "text"},
                          "image": {"type": "text"},
                          "tag": {"type": "text"},
                          "checksum": {"type": "text"},
                        },
                      },
                    }
                }
            }
        }
        "services": {
          "properties": {
            "attributes": {
              "properties": {
                "files": {
                  "type": "text",
                  "fields": {
                    "keyword": {
                      "type": "keyword",
                      "ignore_above": 256
                    }
                  }
                },
                "id": {
                  "type": "text",
                  "fields": {
                    "keyword": {
                      "type": "keyword",
                      "ignore_above": 256
                    }
                  }
                },
                "name": {
                  "type": "text",
                  "fields": {
                    "keyword": {
                      "type": "keyword",
                      "ignore_above": 256
                    }
                  }
                },
                "description": {
                  "type": "text",
                },
                "datatokenAddress": {
                  "type": "text",
                  "fields": {
                    "keyword": {
                      "type": "keyword",
                      "ignore_above": 256
                    }
                  }
                },
                "timeout": {
                  "type": "integer",
                  "fields": {
                    "keyword": {
                      "type": "keyword",
                    }
                  }
                },
                "compute": {
                  "properties": {
                    "allowRawAlgorithm": {
                      "type": "boolean"
                    },
                    "allowNetworkAccess": {
                      "type": "boolean"
                    },
                    "publisherTrustedAlgorithmPublishers": {
                      "type": "text"
                    },
                    "publisherTrustedAlgorithms": {
                      "properties": {
                        "did": {"type": "text"},
                        "filesChecksum": {"type": "text"},
                        "containerSectionChecksum": {"type": "text"},
                      },
                    },
                  }
                }
                "additionalInformation": {
                  "properties": {
                    "structuredMarkup": {
                      "properties": {
                        "mediaType": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        },
                        "uri": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        }
                      }
                    },
                    "updateFrequency": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                        }
                      }
                    },
                    "links": {
                      "properties": {
                        "name": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        },
                        "type": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        },
                        "url": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        }
                      }
                    },
                    "inLanguage": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                        }
                      }
                    },
                    "tags": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256,
                          "normalizer": "ocean_normalizer"
                        }
                      }
                    },
                    "categories": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256,
                          "normalizer": "ocean_normalizer"
                        }
                      }
                    },
                    "copyrightHolder": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                        }
                      }
                    },
                    "description": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256,
                          "normalizer": "ocean_normalizer"
                        }
                      }
                    },
                    "workExample": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                        }
                      }
                    }
                  }
                },
                # TODO: remove main?
                "main": {
                  "properties": {
                    "author": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                        }
                      }
                    },
                    "dateCreated": {
                      "type": "date"
                    },
                    "datePublished": {
                      "type": "date"
                    },
                    "files": {
                      "properties": {
                        "checksum": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        },
                        "checksumType": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        },
                        "compression": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        },
                        "contentLength": {
                          "type": "long"
                        },
                        "contentType": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        },
                        "encoding": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        },
                        "index": {
                          "type": "long"
                        },
                        "resourceId": {
                          "type": "text",
                          "fields": {
                            "keyword": {
                              "type": "keyword",
                              "ignore_above": 256
                            }
                          }
                        }
                      }
                    },
                    "license": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                        }
                      }
                    },
                    "name": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256,
                          "normalizer": "ocean_normalizer"
                        }
                      }
                    },
                    "cost": {
                      "type": "float",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                        }
                      }
                    },
                    "type": {
                      "type": "text",
                      "fields": {
                        "keyword": {
                          "type": "keyword",
                          "ignore_above": 256
                        }
                      }
                    }
                  }
                },
                "curation": {
                  "properties": {
                    "isListed": {
                      "type": "boolean"
                    },
                    "numVotes": {
                      "type": "long"
                    },
                    "rating": {
                      "type": "float"
                    }
                  }
                }
              }
            },
            "serviceEndpoint": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            },
            "type": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            }
          }
        }
      }
    }
  }
}"""
