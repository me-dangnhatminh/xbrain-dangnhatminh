import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Plus, FolderOpen, Database, Calendar, ArrowRight, Building2, Loader2, Trash2 } from 'lucide-react';
import Header from '@/components/layout/Header';
import { useAuth } from '@/hooks/useAuth';

interface KnowledgeBase {
  id: string;
  name: string;
  createdAt: string;
  tenantId: string;
}

export default function KnowledgeBasesPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const tenantId = user?.workspaceId ?? null;
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newKbName, setNewKbName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      navigate('/');
      return;
    }

    const fetchWorkspaces = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL;
        if (!apiUrl) {
          setIsLoading(false);
          return;
        }
        const response = await fetch(`${apiUrl}/workspaces`, {
          headers: { Authorization: `Bearer ${user.idToken}` },
        });
        if (response.ok) {
          const data = await response.json();
          const tenantKbs = data.workspaces.map((ws: any) => ({
              id: ws.workspace_id,
              name: ws.name || ws.tenant_name || ws.workspace_id, // Fallback chain for display name
              createdAt: new Date(ws.created_at).toLocaleDateString('en-GB'),
              tenantId: ws.tenant_id,
            }));
          setKbs(tenantKbs);
        }
      } catch (error) {
        console.error('Lỗi khi tải danh sách workspace:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchWorkspaces();
  }, [user, navigate]);

  const handleCreateKb = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKbName.trim() || !tenantId || !user) return;

    setIsCreating(true);
    const sanitizedId = newKbName.trim().toLowerCase().replace(/[^a-z0-9]/g, '-');

    try {
      const apiUrl = import.meta.env.VITE_API_URL;
      if (apiUrl) {
        await fetch(`${apiUrl}/workspaces`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${user.idToken}`,
          },
          body: JSON.stringify({ workspace_id: sanitizedId, tenant_name: tenantId }),
        });
      }

      const newKb: KnowledgeBase = {
        id: sanitizedId,
        name: sanitizedId,
        createdAt: new Date().toLocaleDateString('en-GB'),
        tenantId,
      };

      setKbs((prev) => [...prev, newKb]);
      setNewKbName('');
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Lỗi khi tạo workspace:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteKb = async (kbId: string) => {
    if (!user) return;
    setDeletingId(kbId);
    try {
      const apiUrl = import.meta.env.VITE_API_URL;
      if (apiUrl) {
        const res = await fetch(`${apiUrl}/workspaces/${kbId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${user.idToken}` },
        });
        if (!res.ok) throw new Error('Delete failed');
      }
      setKbs((prev) => prev.filter((kb) => kb.id !== kbId));
    } catch (error) {
      console.error('Lỗi khi xóa workspace:', error);
      alert('Xóa thất bại. Vui lòng thử lại.');
    } finally {
      setDeletingId(null);
      setConfirmDeleteId(null);
    }
  };

  if (!user) return null;

  const companyName = user.email;

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans selection:bg-blue-100 relative">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
      <div className="absolute left-0 right-0 top-0 h-[500px] w-full bg-gradient-to-b from-blue-50/50 to-transparent pointer-events-none" />

      <div className="relative z-10 flex flex-col flex-1">
        <Header />
        
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8 lg:p-10 animate-in fade-in duration-700 slide-in-from-bottom-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-10 gap-6 border-b border-slate-200/60 pb-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 text-xs font-semibold tracking-wide border border-blue-100">
                  <Building2 className="w-3.5 h-3.5" />
                  {companyName}
                </span>
              </div>
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-900">
                Knowledge Bases
              </h1>
              <p className="text-slate-500 mt-2 text-sm md:text-base max-w-2xl">
                Manage and organize your company's document repositories. Create new knowledge bases to isolate domain-specific information.
              </p>
            </div>
            
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              {/* @ts-ignore */}
              <DialogTrigger asChild>
                <Button className="bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-600/20 transition-all">
                  <Plus className="mr-2 h-4 w-4" />
                  Create Repository
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[460px] p-0 overflow-hidden border-slate-200/60 shadow-2xl">
                <div className="px-6 py-6 bg-slate-50/50 border-b border-slate-100">
                  <DialogHeader>
                    <DialogTitle className="text-xl font-semibold flex items-center gap-2">
                      <Database className="w-5 h-5 text-blue-600" />
                      New Knowledge Base
                    </DialogTitle>
                  </DialogHeader>
                  <p className="text-sm text-slate-500 mt-1.5">
                    Create a dedicated space for specific documents or domains.
                  </p>
                </div>
                
                <form onSubmit={handleCreateKb}>
                  <div className="p-6">
                    <div className="space-y-3">
                      <label htmlFor="name" className="text-sm font-semibold text-slate-700">
                        Repository Name
                      </label>
                      <Input
                        id="name"
                        placeholder="e.g. Q3 Financial Reports, HR Policies..."
                        value={newKbName}
                        onChange={(e: any) => setNewKbName(e.target.value)}
                        className="h-11 focus-visible:ring-blue-500/30"
                        required
                        autoFocus
                      />
                      <p className="text-xs text-slate-400">
                        This name will be converted to a unique identifier automatically.
                      </p>
                    </div>
                  </div>
                  <DialogFooter className="px-6 py-4 bg-slate-50/50 border-t border-slate-100">
                    <Button type="button" variant="ghost" onClick={() => setIsDialogOpen(false)} disabled={isCreating}>
                      Cancel
                    </Button>
                    <Button type="submit" className="bg-blue-600 hover:bg-blue-700 min-w-[100px]" disabled={!newKbName.trim() || isCreating}>
                      {isCreating ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-4" />
              <p className="text-slate-500 text-sm font-medium">Loading repositories...</p>
            </div>
          ) : kbs.length === 0 ? (
            <div className="text-center py-24 bg-white/60 backdrop-blur-sm rounded-2xl border border-dashed border-slate-300 shadow-sm">
              <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-inner border border-blue-100">
                <FolderOpen className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900">No Repositories Found</h3>
              <p className="mt-2 text-sm text-slate-500 max-w-md mx-auto leading-relaxed">
                You haven't created any document repositories yet. Create your first knowledge base to start uploading and querying documents.
              </p>
              <Button onClick={() => setIsDialogOpen(true)} className="mt-8 bg-white hover:bg-slate-50 text-blue-600 border-blue-200 shadow-sm" variant="outline">
                <Plus className="mr-2 h-4 w-4" /> Create First Repository
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {kbs.map((kb) => (
                <Card
                  key={kb.id}
                  className="group flex flex-col bg-white hover:bg-slate-50/50 border-slate-200/60 shadow-sm hover:shadow-md hover:border-blue-200 transition-all duration-300 overflow-hidden cursor-pointer relative"
                  onClick={() => navigate(`/kb?kb_id=${kb.id}`)}
                >
                  <CardHeader className="pb-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="p-2.5 bg-blue-50 rounded-lg group-hover:bg-blue-100 group-hover:scale-110 transition-all duration-300">
                        <Database className="w-5 h-5 text-blue-600" />
                      </div>
                      <div className="flex items-center gap-1">
                        {/* Delete button */}
                        <button
                          onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(kb.id); }}
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50"
                          title="Delete workspace"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 duration-300">
                          <ArrowRight className="w-5 h-5 text-slate-400" />
                        </div>
                      </div>
                    </div>
                    <CardTitle className="text-lg font-semibold text-slate-900 line-clamp-1 group-hover:text-blue-700 transition-colors" title={kb.name}>
                      {kb.name}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1 pb-4">
                    <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
                      <Calendar className="w-3.5 h-3.5" />
                      Created {kb.createdAt}
                    </div>
                  </CardContent>
                  <div className="h-1 w-full bg-gradient-to-r from-blue-500 to-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                </Card>
              ))}
            </div>
          )}
        </main>
      </div>

      {/* Confirm Delete Dialog */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 max-w-sm w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-50 rounded-lg">
                <Trash2 className="w-5 h-5 text-red-500" />
              </div>
              <h3 className="font-semibold text-slate-900">Delete Repository?</h3>
            </div>
            <p className="text-sm text-slate-500 mb-6">
              This will permanently delete <span className="font-semibold text-slate-800">{confirmDeleteId}</span> and all its documents. This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <Button variant="ghost" onClick={() => setConfirmDeleteId(null)} disabled={!!deletingId}>
                Cancel
              </Button>
              <Button
                className="bg-red-500 hover:bg-red-600 text-white"
                onClick={() => handleDeleteKb(confirmDeleteId)}
                disabled={!!deletingId}
              >
                {deletingId === confirmDeleteId ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Delete'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
