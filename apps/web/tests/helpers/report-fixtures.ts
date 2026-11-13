export function reportFixture(
  endpoint: string,
  query: URLSearchParams,
  populated = false,
  zeroNet = false,
) {
  const now = new Date(),
    year = Number(query.get("year") ?? now.getFullYear());
  const start = query.get("date_from") ?? String(year) + "-01-01",
    end = query.get("date_to") ?? String(year) + "-12-31";
  const meta = {
    currency: "EUR",
    date_from: start,
    date_to: end,
    date_basis: "payment_date",
    non_eur_excluded_count: populated ? 2 : 0,
  };
  const amount = (value: string) => (populated ? value : "0.00");
  if (endpoint === "summary")
    return {
      ...meta,
      actual: {
        income: amount("121.30"),
        expenses: amount(zeroNet ? "121.30" : "60.50"),
        net: amount(zeroNet ? "0.00" : "60.80"),
        entry_count: populated ? 4 : 0,
      },
      expected: {
        income: amount("242.00"),
        expenses: amount("12.10"),
        net: amount("229.90"),
        entry_count: populated ? 2 : 0,
      },
      vat: {
        output: amount("20.00"),
        input: amount("10.50"),
        difference: amount("9.50"),
        entry_count: populated ? 3 : 0,
        date_basis: "entry_date",
        non_eur_excluded_count: populated ? 1 : 0,
      },
    };
  if (endpoint === "cash-flow")
    return {
      ...meta,
      grouping: query.get("grouping") ?? "month",
      basis: query.get("basis") ?? "actual",
      entry_count: populated ? 4 : 0,
      items: [
        {
          bucket_start: start,
          date_from: start,
          date_to: end,
          income: amount("121.30"),
          expenses: amount("60.50"),
          net: amount("60.80"),
          entry_count: populated ? 4 : 0,
        },
      ],
    };
  if (endpoint.includes("categories")) {
    const income = endpoint.startsWith("income");
    return {
      ...meta,
      type: income ? "income" : "expense",
      total: amount(income ? "121.30" : "60.50"),
      entry_count: populated ? 1 : 0,
      items: populated
        ? [
            {
              id: "00000000-0000-0000-0000-000000000005",
              name: income ? "Services" : "Software",
              color: "#7250c9",
              active: true,
              amount: income ? "121.30" : "60.50",
              percentage: "100.00",
              entry_count: 1,
            },
          ]
        : [],
    };
  }
  if (endpoint === "pending")
    return {
      currency: "EUR",
      scope: query.get("scope") ?? "period",
      date_from: query.get("scope") === "all" ? null : start,
      date_to: query.get("scope") === "all" ? null : end,
      date_basis: "payment_date",
      as_of: "2026-11-13",
      income: amount("242.00"),
      expenses: amount("12.10"),
      net: amount("229.90"),
      total: populated ? 2 : 0,
      overdue_count: populated ? 1 : 0,
      non_eur_excluded_count: populated ? 1 : 0,
      page: 1,
      page_size: 10,
      items: populated
        ? [
            {
              id: "11111111-1111-4111-8111-111111111111",
              type: "income",
              title: "Pending client payment",
              amount: "242.00",
              currency: "EUR",
              payment_date: start,
              overdue: true,
            },
            {
              id: "22222222-2222-4222-8222-222222222222",
              type: "expense",
              title: "Pending software",
              amount: "12.10",
              currency: "EUR",
              payment_date: end,
              overdue: false,
            },
          ]
        : [],
    };
  if (endpoint === "vat")
    return {
      ...meta,
      date_basis: "entry_date",
      year,
      output: amount("20.00"),
      input: amount("10.50"),
      difference: amount("9.50"),
      entry_count: populated ? 3 : 0,
      quarters: [1, 2, 3, 4].map((q) => ({
        quarter: q,
        date_from:
          String(year) + "-" + String((q - 1) * 3 + 1).padStart(2, "0") + "-01",
        date_to:
          String(year) +
          "-" +
          String(q * 3).padStart(2, "0") +
          "-" +
          (q === 1 || q === 4 ? "31" : "30"),
        output: q === 1 ? amount("20.00") : "0.00",
        input: q === 1 ? amount("10.50") : "0.00",
        difference: q === 1 ? amount("9.50") : "0.00",
        entry_count: q === 1 && populated ? 3 : 0,
      })),
    };
  return {};
}
