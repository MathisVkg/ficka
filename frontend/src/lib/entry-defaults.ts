/**
 * Which value wins when the entry form fills in a VAT rate or a category by itself.
 *
 * VAT rate, highest first:
 *   1. typed by the user                      (user)
 *   2. the default of a category the user picked   (userCategory)
 *   3. a suggestion from a similar entry      (suggestion)
 *   4. the default of a category filled in automatically   (autoCategory)
 *   5. the counterparty's default             (counterparty)
 *   6. the last rate used in this browser     (last)
 *   7. the highest valid rate                 (default)
 * A value the user typed is never replaced.
 *
 * Category: user > suggestion > counterparty default.
 */

export type RateSource =
  'user' | 'userCategory' | 'suggestion' | 'autoCategory' | 'counterparty' | 'last' | 'default';

const RATE_RANK: Record<RateSource, number> = {
  default: 0,
  last: 1,
  counterparty: 2,
  autoCategory: 3,
  suggestion: 4,
  userCategory: 5,
  user: 6
};

/** Should a rate coming from `incoming` replace the one that came from `current`? */
export function rateWins(current: RateSource, incoming: RateSource): boolean {
  if (current === 'user') return false;
  return RATE_RANK[incoming] >= RATE_RANK[current];
}

export type CategorySource = 'user' | 'suggestion' | 'counterparty';

const CATEGORY_RANK: Record<CategorySource, number> = { counterparty: 0, suggestion: 1, user: 2 };

/** Should a category coming from `incoming` replace the current one (`null` = none yet)? */
export function categoryWins(current: CategorySource | null, incoming: CategorySource): boolean {
  if (current === null) return true;
  if (current === 'user') return incoming === 'user';
  return CATEGORY_RANK[incoming] >= CATEGORY_RANK[current];
}

/** The rate source of a category's default, depending on who picked the category. */
export function categoryRateSource(picked: CategorySource): RateSource {
  return picked === 'user' ? 'userCategory' : 'autoCategory';
}
