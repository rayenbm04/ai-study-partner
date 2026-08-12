"use client";

import { ChatCircleDots, Lightning, Plus } from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { analyticsApi, subjectsApi, type OverviewAnalytics, type Subject } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function HomePage() {
  const { user } = useAuth();
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [overview, setOverview] = useState<OverviewAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([subjectsApi.listSubjects(), analyticsApi.getOverview()])
      .then(([subjectList, overviewData]) => {
        setSubjects(subjectList);
        setOverview(overviewData);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const analyticsBySubject = new Map((overview?.subjects ?? []).map((s) => [s.subject_id, s]));
  const dueCount = overview?.total_flashcards_due ?? 0;

  function openCoach(subjectId: string) {
    router.push(`/coach/${subjectId}`);
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Welcome back</p>
          <h1 className="text-2xl font-semibold">{user?.firstname ?? "there"}</h1>
        </div>
        {subjects.length > 0 ? (
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button />}>
              <ChatCircleDots />
              Ask AI Coach
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {subjects.map((subject) => (
                <DropdownMenuItem key={subject.id} onClick={() => openCoach(subject.id)}>
                  {subject.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : null}
      </div>

      <Card className="bg-primary/5">
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
              <Lightning weight="fill" className="size-6" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Today&apos;s mission</p>
              <p className="text-lg font-semibold">
                {isLoading ? "Loading…" : dueCount > 0 ? `${dueCount} cards due` : "All caught up"}
              </p>
              <p className="text-sm text-muted-foreground">
                {dueCount > 0 ? "Keep your streak going." : "Nothing due right now — review ahead if you like."}
              </p>
            </div>
          </div>
          <Button render={<Link href="/cards" />} nativeButton={false} className="w-fit">
            {dueCount > 0 ? "Continue reviewing" : "Review anyway"}
          </Button>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Your subjects</h2>
        <Button render={<Link href="/subjects/new" />} nativeButton={false} variant="secondary" size="sm">
          <Plus />
          New subject
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      ) : subjects.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <p className="font-medium">No subjects yet</p>
            <p className="text-sm text-muted-foreground">
              Add a subject to start uploading documents and generating study material.
            </p>
            <Button render={<Link href="/subjects/new" />} nativeButton={false} variant="secondary">
              New subject
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {subjects.map((subject) => {
            const stats = analyticsBySubject.get(subject.id);
            const mastery = stats?.average_mastery ?? null;
            return (
              <Link key={subject.id} href={`/subjects/${subject.id}`}>
                <Card className="transition-colors hover:bg-accent/50">
                  <CardContent className="flex flex-col gap-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="flex size-11 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white"
                        style={{ backgroundColor: subject.color ?? "var(--muted-foreground)" }}
                      >
                        {subject.name.slice(0, 2).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{subject.name}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {stats
                            ? `${stats.concepts_practiced}/${stats.concepts_total} concepts practiced`
                            : "No documents yet"}
                        </p>
                      </div>
                      <p className="text-lg font-semibold text-primary">
                        {mastery !== null ? `${Math.round(mastery)}%` : "—"}
                      </p>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${Math.max(4, mastery ?? 4)}%` }}
                      />
                    </div>
                    {stats && stats.flashcards_due_count > 0 ? (
                      <span className="w-fit rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                        {stats.flashcards_due_count} due
                      </span>
                    ) : null}
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
