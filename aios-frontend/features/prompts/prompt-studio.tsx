"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { PromptListPanel } from "./prompt-list-panel";
import { PromptEditor, PromptDiffViewer } from "./prompt-editor";
import { VariablesPanel } from "./variables-panel";
import { extractVariables, renderTemplate } from "./extract-variables";
import { prompts as seedPrompts } from "@/lib/mock-data";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CheckCircle2, History, Rocket, Save, Sparkles } from "lucide-react";
import { useAutosave } from "@/hooks/use-autosave";
import { useDraftStore } from "@/stores/draft-store";

export function PromptStudio() {
  const [selectedPromptId, setSelectedPromptId] = useState(seedPrompts[0].id);
  const prompt = seedPrompts.find((p) => p.id === selectedPromptId)!;
  const [content, setContent] = useState(prompt.versions[0].content);
  const [compareVersionId, setCompareVersionId] = useState(prompt.versions[1]?.id ?? prompt.versions[0].id);
  const [values, setValues] = useState<Record<string, string>>({});
  const draftKey = `prompt:${selectedPromptId}`;
  const drafts = useDraftStore((s) => s.drafts);

  useAutosave(draftKey, content);

  const variables = useMemo(() => extractVariables(content), [content]);
  const rendered = useMemo(() => renderTemplate(content, values), [content, values]);
  const compareVersion = prompt.versions.find((v) => v.id === compareVersionId) ?? prompt.versions[0];
  const hasUnsavedDraft = drafts[draftKey] && drafts[draftKey] !== prompt.versions[0].content;

  function selectPrompt(id: string) {
    const p = seedPrompts.find((pp) => pp.id === id)!;
    setSelectedPromptId(id);
    setContent(p.versions[0].content);
    setCompareVersionId(p.versions[1]?.id ?? p.versions[0].id);
    setValues({});
  }

  return (
    <div className="h-[calc(100vh-9.5rem)] overflow-hidden rounded-xl border border-border">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={22} minSize={16} maxSize={32}>
          <div className="flex h-full flex-col">
            <div className="border-b border-border px-3 py-2.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Prompts</p>
            </div>
            <PromptListPanel prompts={seedPrompts} selectedId={selectedPromptId} onSelect={selectPrompt} />
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />

        <ResizablePanel defaultSize={53} minSize={35}>
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <div>
                <p className="text-sm font-semibold">{prompt.name}</p>
                <p className="text-xs text-muted-foreground">Target model: {prompt.targetModel}</p>
              </div>
              <div className="flex items-center gap-2">
                {hasUnsavedDraft && (
                  <Badge variant="warning" className="gap-1">
                    <Save className="h-3 w-3" /> Draft autosaved
                  </Badge>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => toast.success("Version saved", { description: `${prompt.name} — new draft version created` })}
                >
                  <Save className="h-3.5 w-3.5" /> Save version
                </Button>
                <Button size="sm" onClick={() => toast.success("Promoted to production", { description: "Gated by Evaluation Engine — score 94.2%" })}>
                  <Rocket className="h-3.5 w-3.5" /> Promote
                </Button>
              </div>
            </div>
            <Tabs defaultValue="editor" className="flex flex-1 flex-col overflow-hidden">
              <div className="border-b border-border px-3 pt-2">
                <TabsList>
                  <TabsTrigger value="editor">Editor</TabsTrigger>
                  <TabsTrigger value="preview">Preview</TabsTrigger>
                  <TabsTrigger value="diff">Compare versions</TabsTrigger>
                </TabsList>
              </div>
              <TabsContent value="editor" className="mt-0 flex-1 overflow-hidden">
                <PromptEditor value={content} onChange={setContent} />
              </TabsContent>
              <TabsContent value="preview" className="mt-0 flex-1 overflow-y-auto scrollbar-thin p-4">
                <p className="mb-2 text-xs font-medium text-muted-foreground">Rendered with current variable values</p>
                <pre className="whitespace-pre-wrap rounded-lg border border-border bg-muted/40 p-4 font-mono text-sm">{rendered}</pre>
              </TabsContent>
              <TabsContent value="diff" className="mt-0 flex-1 overflow-hidden">
                <div className="flex h-full flex-col">
                  <div className="flex items-center gap-2 border-b border-border px-3 py-2">
                    <span className="text-xs text-muted-foreground">Compare current draft against</span>
                    <Select value={compareVersionId} onValueChange={setCompareVersionId}>
                      <SelectTrigger className="h-7 w-40 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {prompt.versions.map((v) => (
                          <SelectItem key={v.id} value={v.id}>
                            v{v.version} · {v.status}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex-1">
                    <PromptDiffViewer original={compareVersion.content} modified={content} />
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />

        <ResizablePanel defaultSize={25} minSize={20} maxSize={36}>
          <div className="flex h-full flex-col gap-4 overflow-y-auto scrollbar-thin p-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
                  <Sparkles className="h-3.5 w-3.5" /> Variables
                </CardTitle>
              </CardHeader>
              <CardContent>
                <VariablesPanel variables={variables} values={values} onChange={(name, v) => setValues((s) => ({ ...s, [name]: v }))} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
                  <History className="h-3.5 w-3.5" /> Version history
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {prompt.versions.map((v) => (
                  <div key={v.id} className="flex items-center justify-between rounded-md border border-border px-2.5 py-2 text-xs">
                    <div>
                      <p className="font-medium">
                        v{v.version} <span className="font-normal text-muted-foreground">by {v.author}</span>
                      </p>
                      <p className="text-muted-foreground">{new Date(v.createdAt).toLocaleDateString()}</p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {v.evalScore != null && (
                        <span className="flex items-center gap-1 font-mono text-success">
                          <CheckCircle2 className="h-3 w-3" /> {v.evalScore}%
                        </span>
                      )}
                      <Badge
                        variant={v.status === "production" ? "success" : v.status === "staged" ? "warning" : "secondary"}
                        className="text-[10px]"
                      >
                        {v.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
