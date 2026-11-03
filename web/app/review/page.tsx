"use client";

import { useEffect, useState } from "react";
import { fetchReviewQueue, postReviewAction } from "../../lib/api/client";
import { useLocale } from "../../lib/hooks/useLocale";
import { t } from "../../lib/i18n";

type Item = { id: string; control_id: string; outcome: string };

export default function ReviewPage() {
  const locale = useLocale();
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => {
    fetchReviewQueue().then((rows) => setItems(rows as Item[]));
  }, []);

  const run = async (id: string, action: string) => {
    await postReviewAction(id, action);
  };

  return (
    <section data-testid="page-review">
      <h1>{t(locale, "review.heading")}</h1>
      <p>{t(locale, "review.description")}</p>
      {items.length === 0 ? (
        <p>{t(locale, "review.empty")}</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <span>{item.control_id}</span>{" "}
              <button type="button" onClick={() => run(item.id, "validate")}>
                {t(locale, "actions.validate")}
              </button>{" "}
              <button type="button" onClick={() => run(item.id, "reject")}>
                {t(locale, "actions.reject")}
              </button>{" "}
              <button type="button" onClick={() => run(item.id, "modify")}>
                {t(locale, "actions.modify")}
              </button>{" "}
              <button type="button" onClick={() => run(item.id, "annotate")}>
                {t(locale, "actions.annotate")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
