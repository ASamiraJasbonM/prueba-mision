# Fuentes técnicas consultadas

- Django: https://www.djangoproject.com/download/ (rama elegida 5.2 LTS, versiones exactas en pyproject.toml + uv.lock).
- DRF: https://www.django-rest-framework.org/community/3.16-announcement/
- World Bank: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures
- ExchangeRate-API: https://www.exchangerate-api.com/docs/free (endpoint open.er-api.com/v6/latest/USD, sin clave, actualización diaria; requiere atribución «Rates By Exchange Rate API» enlazada a https://www.exchangerate-api.com en la UI que utilice tasas).
- REST Countries: https://restcountries.com/docs y https://restcountries.com/docs/countries (v5, bearer token por variable de entorno; el typo `contries` del PDF se corrige).

Consulta: 17-nov-2026. La documentación consultada no equivale a probar una sincronización real. Tests HTTP usan respuestas controladas; un proveedor caído o clave ausente conserva datos anteriores. No se usa el servicio adicional de divisas de REST Countries.
