## Summary

Describe the user-visible outcome and why this change is needed.

## Verification

- [ ] `make lint`
- [ ] `make test`
- [ ] `cd dashboard && npm test -- --runInBand`
- [ ] `make build`
- [ ] Browser or integration checks where relevant

## Safety

- [ ] Holdout separation and statistical gates remain intact.
- [ ] Organization scoping and secret scrubbing remain intact.
- [ ] No real customer traces, credentials, or generated secrets are included.
