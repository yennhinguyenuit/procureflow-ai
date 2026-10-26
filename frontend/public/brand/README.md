# Authorized workspace assets

ProcureFlow uses its own neutral wordmark by default. No Trung Nguyen Legend logo, official brand asset, or corporate endorsement is included.

Only add an asset here when its owner has authorized this specific use. Keep the approval and applicable attribution with your project records. To enable an approved local image, set both build-time variables:

```env
VITE_BRAND_ASSET_AUTHORIZED=true
VITE_AUTHORIZED_BRAND_ASSET=/brand/approved-workspace.png
```

The component accepts a direct local `/brand/` filename ending in `.svg`, `.png`, or `.webp`. External URLs, nested paths, and query strings are rejected. The authorization flag is an explicit operator assertion, not a grant of rights. Rebuild after changing these values. The application help panel retains the academic/non-affiliation notice.
