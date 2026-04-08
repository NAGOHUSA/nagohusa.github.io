/**
 * listings.js — Central data file for all marketplace app listings.
 *
 * To add a new app:
 *   1. Duplicate one of the objects below.
 *   2. Fill in all fields (especially stripePaymentLink and repo).
 *   3. In your Stripe Payment Link settings:
 *      - Add a "Custom Field" with key `github_username` (type: text) so buyers
 *        can enter their GitHub handle at checkout.
 *      - Under "Metadata", set `repo_name` to the short repo name (e.g. "my-app-ios").
 *        This tells the webhook which repo to grant access to.
 *   4. Commit and push — the storefront updates automatically.
 */

const LISTINGS = [
  {
    /** Unique slug — used in URLs and as a CSS/HTML id */
    id: "swift-commerce-kit",

    /** Display name shown on the card */
    name: "SwiftCommerce Kit",

    /** One-line tagline */
    tagline: "Full-featured e-commerce iOS app with Stripe + SwiftUI",

    /** Longer description shown on the card */
    description:
      "A production-ready Xcode project for building iOS shopping apps. " +
      "Includes product catalog, cart, Stripe payment sheet, order history, " +
      "push notifications, and a Firebase backend — all in SwiftUI.",

    /** Human-readable price string shown to buyers */
    priceDisplay: "$79",

    /**
     * Stripe Payment Link URL.
     * Create one at https://dashboard.stripe.com/payment-links
     * Remember to:
     *   • Add Custom Field key `github_username`
     *   • Add Metadata key `repo_name` = the private repo short name
     */
    stripePaymentLink: "https://buy.stripe.com/REPLACE_WITH_YOUR_LINK",

    /**
     * Short name of the private GitHub repo to grant access to.
     * Must match the `repo_name` metadata value on the Stripe Payment Link.
     */
    repo: "swift-commerce-kit-ios",

    /** Emoji or URL to a 512×512 PNG icon */
    icon: "🛍️",

    /** Tech tags shown as badges */
    tags: ["SwiftUI", "iOS 17+", "Stripe", "Firebase", "Xcode 15"],

    /** Bullet points shown on the card */
    features: [
      "Complete Xcode project (Swift Package Manager)",
      "Stripe Payment Sheet integration",
      "Firebase Auth + Firestore",
      "Full source code & inline comments",
      "Free updates for 12 months",
    ],
  },

  {
    id: "ai-chat-ios",
    name: "AI Chat Pro",
    tagline: "ChatGPT-powered iOS chat app with streaming responses",
    description:
      "Drop-in Xcode project that wraps the OpenAI Chat Completions API. " +
      "Features message streaming, conversation history, system prompt editor, " +
      "and a polished SwiftUI interface with dark/light mode support.",
    priceDisplay: "$49",
    stripePaymentLink: "https://buy.stripe.com/REPLACE_WITH_YOUR_LINK_2",
    repo: "ai-chat-pro-ios",
    icon: "🤖",
    tags: ["SwiftUI", "OpenAI", "Streaming", "iOS 16+", "Xcode 15"],
    features: [
      "Streaming responses via URLSession AsyncBytes",
      "Conversation history with Core Data",
      "System prompt & model switcher",
      "Dark / light mode",
      "Full source code",
    ],
  },

  {
    id: "fitness-tracker-ios",
    name: "FitTrack Pro",
    tagline: "HealthKit workout tracker with beautiful charts",
    description:
      "A complete iOS fitness tracking Xcode project built with SwiftUI and " +
      "HealthKit. Log workouts, visualise progress with Swift Charts, set goals, " +
      "and share achievements — ready to submit to the App Store.",
    priceDisplay: "$59",
    stripePaymentLink: "https://buy.stripe.com/REPLACE_WITH_YOUR_LINK_3",
    repo: "fittrack-pro-ios",
    icon: "💪",
    tags: ["SwiftUI", "HealthKit", "Swift Charts", "iOS 17+", "Xcode 15"],
    features: [
      "HealthKit read & write integration",
      "Swift Charts workout visualisations",
      "Goal setting & streak tracking",
      "App Store-ready (includes metadata)",
      "Full source code",
    ],
  },
];
