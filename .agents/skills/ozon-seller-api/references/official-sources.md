# Official sources

Use current first-party Ozon documentation as the source of truth:

- Seller API reference: https://docs.ozon.ru/api/seller/
- Ozon developer news and API-key changes: https://dev.ozon.ru/news/
- Seller API service origin: https://api-seller.ozon.ru

Before implementation:

1. Locate the exact operation in the live Seller API reference.
2. Record its HTTP method, versioned path, required headers, request schema, response schema, pagination, limits, and documented errors.
3. Check developer news for recent authentication, permission, or deprecation changes.
4. Prefer current examples from Ozon. Treat community SDKs, copied Postman collections, blog posts, and marketplace analytics services as secondary evidence only.
5. Do not silently substitute MPStats or another third-party marketplace API for Ozon Seller API.

The commonly documented Seller API authentication headers are `Client-Id` and `Api-Key`; verify current requirements and key scope in Ozon documentation for every implementation.
