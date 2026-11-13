"use client";
import { useState } from "react";
import { CalendarDays } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Period, periodFor } from "@/lib/api/reporting";
export function PeriodSelector({
  value,
  onChange,
}: {
  value: Period;
  onChange: (value: Period) => void;
}) {
  const [start, setStart] = useState(value.start),
    [end, setEnd] = useState(value.end),
    [error, setError] = useState("");
  return (
    <div className="report-period">
      <label className="period">
        <CalendarDays size={16} />
        <span className="sr-only">Reporting period</span>
        <select
          aria-label="Reporting period"
          value={value.preset}
          onChange={(e) =>
            onChange(
              e.target.value === "custom"
                ? { ...value, preset: "custom" }
                : periodFor(e.target.value),
            )
          }
        >
          <option value="month">This month</option>
          <option value="last-month">Last month</option>
          <option value="quarter">This quarter</option>
          <option value="year">This year</option>
          <option value="ytd">Year to date</option>
          <option value="6-months">6 months</option>
          <option value="12-months">12 months</option>
          <option value="custom">Custom range</option>
        </select>
      </label>
      {value.preset === "custom" && (
        <form
          className="custom-period"
          onSubmit={(event) => {
            event.preventDefault();
            if (!start || !end || start > end) {
              setError("Choose valid dates with start on or before end.");
              return;
            }
            setError("");
            onChange({ preset: "custom", start, end });
          }}
        >
          <label>
            From
            <input
              aria-label="Report start date"
              type="date"
              required
              min="1900-01-01"
              max="2100-12-31"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label>
            To
            <input
              aria-label="Report end date"
              type="date"
              required
              min="1900-01-01"
              max="2100-12-31"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
          <Button type="submit" size="sm" variant="outline">
            Apply range
          </Button>
          {error && (
            <small role="alert" className="field-error">
              {error}
            </small>
          )}
        </form>
      )}
    </div>
  );
}
