"use client";

import {
  BookOpen,
  CalendarBlank,
  ChartLine,
  Gear,
  House,
  Plus,
  SignOut,
  Stack,
} from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupAction,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { subjectsApi, type Subject } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { title: "Home", url: "/", icon: House },
  { title: "Cards", url: "/cards", icon: Stack },
  { title: "Study Plan", url: "/study-plan", icon: CalendarBlank },
  { title: "Progress", url: "/progress", icon: ChartLine },
  { title: "Settings", url: "/settings", icon: Gear },
];

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [subjects, setSubjects] = useState<Subject[]>([]);

  useEffect(() => {
    subjectsApi.listSubjects().then(setSubjects).catch(() => setSubjects([]));
  }, []);

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/" />}>
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <BookOpen className="size-4" />
              </div>
              <span className="font-semibold">AI Study Partner</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => (
                <SidebarMenuItem key={item.url}>
                  <SidebarMenuButton isActive={pathname === item.url} render={<Link href={item.url} />}>
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Subjects</SidebarGroupLabel>
          <SidebarGroupAction title="Add subject" render={<Link href="/subjects/new" />}>
            <Plus />
          </SidebarGroupAction>
          <SidebarGroupContent>
            <SidebarMenu>
              {subjects.map((subject) => (
                <SidebarMenuItem key={subject.id}>
                  <SidebarMenuButton
                    isActive={pathname === `/subjects/${subject.id}`}
                    render={<Link href={`/subjects/${subject.id}`} />}
                  >
                    <span
                      className="size-2 shrink-0 rounded-full"
                      style={{ backgroundColor: subject.color ?? "var(--muted-foreground)" }}
                    />
                    <span className="truncate">{subject.name}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton render={<Link href="/settings" />}>
              <div className="flex size-6 items-center justify-center rounded-full bg-muted text-xs font-medium">
                {user?.firstname?.[0]?.toUpperCase() ?? "?"}
              </div>
              <span className="truncate">{user ? `${user.firstname} ${user.lastname}` : "Loading…"}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={handleLogout}>
              <SignOut />
              <span>Sign out</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
