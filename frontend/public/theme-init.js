/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
(function() {
  try {
    var theme = null;
    var a11y = localStorage.getItem('accessibility-settings');
    if (a11y) {
      var parsed = JSON.parse(a11y);
      if (parsed.theme) theme = parsed.theme;
    }
    if (!theme) {
      var stored = localStorage.getItem('lsc-preferences');
      if (stored) {
        var prefs = JSON.parse(stored);
        if (prefs.theme) theme = prefs.theme;
      }
    }
    // L30: dark is default, only switch to light if explicitly set
    if (theme === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.add('dark');
    }
  } catch (e) {
    document.documentElement.classList.add('dark');
  }
  // Prevent transition flicker during initial render
  document.documentElement.classList.add('no-transitions');
  // Set body background immediately to prevent white flash
  document.documentElement.style.backgroundColor = (theme === 'light') ? '#FAF8FA' : '#1E1A24';
  window.addEventListener('load', function() {
    // Remove after first paint + one frame
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        document.documentElement.classList.remove('no-transitions');
      });
    });
  });
})();
