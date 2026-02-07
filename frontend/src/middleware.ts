import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Define protected routes - dashboard requires authentication
const isProtectedRoute = createRouteMatcher(["/dashboard(.*)"]);

// Define public routes - landing page is always accessible
const isPublicRoute = createRouteMatcher(["/"]);

export default clerkMiddleware(async (auth, req) => {
    // If trying to access a protected route, require authentication
    if (isProtectedRoute(req)) {
        await auth.protect();
    }
});

export const config = {
    // Match all routes except static files and Next.js internals
    matcher: [
        // Skip Next.js internals and all static files
        "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
        // Always run for API routes
        "/(api|trpc)(.*)",
    ],
};
