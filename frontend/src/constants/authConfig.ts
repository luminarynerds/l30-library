/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Authentication configuration and validation rules
 */

/**
 * Common weak passwords blocked by the backend.
 * Kept in sync with backend/app/core/security.py COMMON_PASSWORDS.
 */
export const COMMON_PASSWORDS: Set<string> = new Set([
  'password',
  'password123',
  '123456',
  '12345678',
  'qwerty',
  'abc123',
  'monkey',
  '1234567',
  'letmein',
  'trustno1',
  'dragon',
  'baseball',
  'iloveyou',
  'master',
  'sunshine',
  'ashley',
  'foobar',
  'passw0rd',
  'shadow',
  '123123',
  '654321',
  'superman',
  'qazwsx',
  'michael',
  'football',
  'password1',
  'password12',
  'princess',
  'admin',
  'welcome',
])


export function getCardConfig(cardPrefix: string) {
  const numDigits = 6
  return {
    PREFIX: cardPrefix,
    LENGTH: cardPrefix.length + numDigits,
    NUM_DIGITS: numDigits,
    PATTERN: new RegExp(`^${cardPrefix}\\d{${numDigits}}$`),
    EXAMPLE: `${cardPrefix}123456`,
    MESSAGES: {
      CARD_REQUIRED: "Pop in your library card number - you'll find it on your physical card",
      CARD_INVALID: `Library card numbers look like ${cardPrefix} followed by ${numDigits} digits - for example, ${cardPrefix}123456. Check your physical card!`,
    },
  }
}

const DEFAULT_CARD = getCardConfig('LSC')

export const AUTH_CONFIG = {
  // Password requirements
  PASSWORD: {
    MIN_LENGTH: 8,
    REQUIRE_DIGIT: true,
    REQUIRE_LOWERCASE: true,
    REQUIRE_UPPERCASE: true,
    REQUIRE_SPECIAL_CHAR: true,
  },

  // Library card format
  LIBRARY_CARD: {
    PREFIX: DEFAULT_CARD.PREFIX,
    LENGTH: DEFAULT_CARD.LENGTH,
  },

  // PIN requirements
  PIN: {
    MIN_LENGTH: 4,
    MAX_LENGTH: 6,
  },

  // UI timeouts (ms)
  TIMEOUTS: {
    MODAL_SUCCESS: 1500,
    PAGE_SUCCESS: 2500,
    PASSWORD_RESET_SUCCESS: 3000,
  },

  // Validation messages - warm, supportive, and community-focused
  VALIDATION_MESSAGES: {
    EMAIL_REQUIRED: "We'll need your email to keep you updated on your account",
    EMAIL_INVALID: "That email doesn't look quite right. It should look something like: name@example.com",
    PASSWORD_REQUIRED: "Please enter your password",
    PASSWORD_TOO_SHORT: "Your password needs to be at least 8 characters - a bit longer for better security!",
    PASSWORD_NEEDS_DIGIT: 'Add a number to your password (0-9) to make it stronger',
    PASSWORD_NEEDS_LOWERCASE: 'Add a lowercase letter (a-z) to make it stronger',
    PASSWORD_NEEDS_UPPERCASE: 'Add an uppercase letter (A-Z) to make it stronger',
    PASSWORD_NEEDS_SPECIAL: 'Add a special character (like ! @ # $) to make it stronger',
    PASSWORD_TOO_COMMON: "That password is too easy to guess. Try something more unique that only you would know!",
    PASSWORD_MISMATCH: "Those passwords don't match. Try typing them both again?",
    CARD_REQUIRED: DEFAULT_CARD.MESSAGES.CARD_REQUIRED,
    CARD_INVALID: DEFAULT_CARD.MESSAGES.CARD_INVALID,
    PIN_REQUIRED: 'Your PIN is the 4-6 digit number you created when you signed up',
    PIN_INVALID: 'PINs are 4 to 6 digits, numbers only - like 1234 or 123456',
    PHONE_INVALID: "That phone number doesn't look quite right. Please double-check and try again.",
    FIRST_NAME_REQUIRED: "What should we call you? Your first name helps us personalize your experience",
    LAST_NAME_REQUIRED: "We'll need your last name too",
  },

  // Error codes from API
  ERROR_CODES: {
    INVALID_CREDENTIALS: 401,
    ACCOUNT_LOCKED: 423,
    RATE_LIMITED: 429,
    SERVER_ERROR: 500,
  },

  // Error messages - warm, supportive, and helpful
  ERROR_MESSAGES: {
    RATE_LIMITED: "Whoa, that's a lot of attempts! Let's take a 5-minute breather, then try again. If you're having trouble remembering your password, the 'Forgot Password' link is there for you.",
    ACCOUNT_LOCKED: "For your security, we've temporarily locked this account after several login attempts. You can try again in 30 minutes, or stop by the library and we'll help sort it out.",
    INVALID_CREDENTIALS: "Hmm, we couldn't find that combination. Double-check your email and password? If you've forgotten your password, the 'Forgot Password' link can help you get back in.",
    NETWORK_ERROR: "It looks like we've lost our connection. Here's what you can try:\n1. Check that your WiFi or internet is connected\n2. Refresh the page\n3. Wait a moment and try again\n\nIf you're still having trouble, stop by the library — we're happy to help!",
    SERVER_ERROR: "Our system is taking a quick break right now. We're working on it! Please try again in a few minutes.",
    GENERIC_LOGIN_FAILED: "Hmm, we couldn't sign you in. Double-check your email and password? If you've forgotten your password, the 'Forgot Password' link can help you get back in.",
    GENERIC_REGISTER_FAILED: "We weren't able to create your account just yet. This usually happens when:\n- The email address is already in use\n- The password doesn't meet our requirements\n- There's a connection hiccup\n\nGive it another try, and if it's still not working, stop by the library — we're here to help.",
  },
}
