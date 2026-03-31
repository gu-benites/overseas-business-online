• I’m comparing this branch against main and tracing the identity/locale/browser startup path end to end. The question is not just the locale bug
  itself, but which branch-specific changes increase Google distrust and therefore captcha rate.

• I’m focusing on the browser startup path because that’s where locale, timezone, and other fingerprinting signals are set before the first Google request.

• I’ve confirmed the locale bug was introduced in this dirty migration worktree, not inherited from main. Next I’m checking the remaining identity
  mismatches that would still make Google trust this branch less than the old ARM box.