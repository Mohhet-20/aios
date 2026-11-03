"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";
import { Fragment } from "react";

/** Auto-derived from the URL path so every new route gets breadcrumbs for
 *  free — no per-page config to keep in sync. */
export function Breadcrumbs() {
  const pathname = usePathname() ?? "/dashboard";
  const segments = pathname.split("/").filter(Boolean);

  const crumbs = segments.map((seg, idx) => {
    const href = "/" + segments.slice(0, idx + 1).join("/");
    const label = seg
      .split("-")
      .map((w) => w[0]?.toUpperCase() + w.slice(1))
      .join(" ");
    return { href, label };
  });

  return (
    <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <Link href="/dashboard" className="flex items-center hover:text-foreground">
        <Home className="h-3.5 w-3.5" />
      </Link>
      {crumbs.map((c, i) => (
        <Fragment key={c.href}>
          <ChevronRight className="h-3.5 w-3.5 opacity-50" />
          {i === crumbs.length - 1 ? (
            <span className="font-medium text-foreground">{c.label}</span>
          ) : (
            <Link href={c.href} className="hover:text-foreground">
              {c.label}
            </Link>
          )}
        </Fragment>
      ))}
    </nav>
  );
}
