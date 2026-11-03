import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { TraceWaterfall } from "@/features/monitoring/trace-waterfall";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const recentTraces = [
  { id: "tr_88a2f1", route: "POST /v1/agents/ag_1/run", duration: "460ms", status: "success" },
  { id: "tr_77c910", route: "POST /v1/workflows/wf_1/execute", duration: "2.1s", status: "success" },
  { id: "tr_1290ab", route: "POST /v1/agents/ag_4/run", duration: "1.8s", status: "error" },
  { id: "tr_bb3f02", route: "POST /v1/evaluation/runs", duration: "5.4s", status: "success" },
];

export default function ObservabilityPage() {
  return (
    <div>
      <PageHeader title="Observability" description="Distributed traces across every engine — from gateway to provider and back." />

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Trace tr_88a2f1</CardTitle>
          <CardDescription>POST /v1/agents/ag_1/run · 460ms total · claude-haiku-4.5</CardDescription>
        </CardHeader>
        <CardContent>
          <TraceWaterfall />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent traces</CardTitle>
          <CardDescription>Click any row in a real deployment to open its waterfall.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Trace ID</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentTraces.map((t) => (
                <TableRow key={t.id}>
                  <TableCell className="font-mono text-xs">{t.id}</TableCell>
                  <TableCell className="font-mono text-xs">{t.route}</TableCell>
                  <TableCell className="font-mono text-xs">{t.duration}</TableCell>
                  <TableCell>
                    <Badge variant={t.status === "error" ? "destructive" : "success"}>{t.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
