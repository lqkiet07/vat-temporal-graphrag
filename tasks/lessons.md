# Lessons Learned

## Error Pattern: Unimported JSX Icon in React Component
- **Symptom**: Page goes completely blank white when rendering a greeting message or specific conditional branch.
- **Root Cause**: An icon component (`<Sparkles />`) was added in a JSX ternary/conditional branch in `App.tsx`, but was not imported from `lucide-react`. When that branch triggered at runtime, JavaScript threw an uncaught `ReferenceError: Sparkles is not defined`, causing React 18 to unmount the entire tree without a top-level ErrorBoundary.
- **Rules to Prevent Recurrence**:
  1. Always verify that EVERY JSX component tag has a matching import statement. Run a regex or AST check script if editing large TSX files.
  2. Always wrap root components with a top-level `<ErrorBoundary>` in `main.tsx` so unhandled runtime errors display a recovery UI with a reload button rather than a blank white screen.
  3. Ensure array properties (`citations`, `audit`, `application`) in API response objects are guarded with `?.` or default fallbacks `[]` before `.map()` to prevent `TypeError: cannot read properties of undefined`.
