"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { models } from "@/lib/mock-data";
import { Plus } from "lucide-react";

const agentSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(60),
  role: z.string().min(2, "Role is required"),
  model: z.string().min(1, "Select a model"),
  description: z.string().max(280).optional(),
});

type AgentFormValues = z.infer<typeof agentSchema>;

/**
 * Demonstrates the platform's standard form pattern: React Hook Form + Zod
 * schema validation + inline field errors + optimistic toast on submit.
 * Every "create X" dialog across the product (agents, prompts, workflows,
 * API keys) follows this same shape.
 */
export function CreateAgentDialog() {
  const [open, setOpen] = useState(false);
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<AgentFormValues>({ resolver: zodResolver(agentSchema) });

  async function onSubmit(values: AgentFormValues) {
    await new Promise((r) => setTimeout(r, 600));
    toast.success(`Agent "${values.name}" created`, { description: `Model: ${values.model}` });
    reset();
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4" /> New agent
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create agent</DialogTitle>
          <DialogDescription>Define a specialized agent with a role, model, and description.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" placeholder="e.g. Billing Support Agent" {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="role">Role</Label>
            <Input id="role" placeholder="e.g. Classifier, Retriever, Specialist" {...register("role")} />
            {errors.role && <p className="text-xs text-destructive">{errors.role.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>Model</Label>
            <Select onValueChange={(v) => setValue("model", v, { shouldValidate: true })} value={watch("model")}>
              <SelectTrigger>
                <SelectValue placeholder="Select a model" />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.model && <p className="text-xs text-destructive">{errors.model.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Input id="description" placeholder="What does this agent do?" {...register("description")} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create agent"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
