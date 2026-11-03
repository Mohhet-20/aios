"use client";

import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { LiveState } from "./live-state";

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
}

/** A table of records from a live service, with honest loading, error and empty states. */
export function LiveTable<T extends { id?: string; name?: string }>({
  query,
  columns,
  empty,
  rowKey,
  caption,
}: {
  query: { data: T[] | undefined; isLoading: boolean; error: unknown };
  columns: Column<T>[];
  empty: ReactNode;
  rowKey?: (row: T) => string;
  caption?: string;
}) {
  return (
    <Card>
      <CardContent className="p-0">
        <LiveState
          query={query}
          isEmpty={(rows) => rows.length === 0}
          empty={empty}
          skeleton={
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          }
        >
          {(rows) => (
            <Table aria-label={caption}>
              <TableHeader>
                <TableRow>
                  {columns.map((c) => (
                    <TableHead key={c.header} className={c.className}>
                      {c.header}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row, i) => (
                  <TableRow key={rowKey?.(row) ?? row.id ?? row.name ?? i}>
                    {columns.map((c) => (
                      <TableCell key={c.header} className={c.className}>
                        {c.cell(row)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </LiveState>
      </CardContent>
    </Card>
  );
}

/** Name plus optional description, the first column of most tables. */
export function NameCell({ name, description }: { name: string; description: string | null }) {
  return (
    <div className="min-w-0">
      <p className="font-medium">{name}</p>
      {description && <p className="max-w-md truncate text-xs text-muted-foreground">{description}</p>}
    </div>
  );
}
