import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Plus, FolderOpen, Database, Calendar, ArrowRight, Building2, Loader2, Trash2, Search } from 'lucide-react';
import Header from '@/components/layout/Header';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

interface KnowledgeBase {
  id: string;
  name: string;
  createdAt: string;
}

export default function KnowledgeBasesPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
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
              name: ws.name || ws.workspace_id,
              createdAt: new Date(ws.created_at).toLocaleDateString('en-GB'),
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
    if (!newKbName.trim() || !user) return;

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
          body: JSON.stringify({ workspace_id: sanitizedId, name: newKbName.trim() }),
        });
      }

      const newKb: KnowledgeBase = {
        id: sanitizedId,
        name: newKbName.trim(),
        createdAt: new Date().toLocaleDateString('en-GB'),
      };

      setKbs((prev) => [...prev, newKb]);
      setNewKbName('');
      setIsDialogOpen(false);
      toast.success('Workspace created successfully!');
    } catch (error) {
      console.error('Lỗi khi tạo workspace:', error);
      toast.error('Failed to create workspace.');
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
      toast.success('Workspace deleted successfully');
    } catch (error) {
      console.error('Lỗi khi xóa workspace:', error);
      toast.error('Failed to delete workspace.');
    } finally {
      setDeletingId(null);
      setConfirmDeleteId(null);
    }
  };

  const filteredKbs = useMemo(() => {
    if (!searchQuery.trim()) return kbs;
    return kbs.filter(kb => kb.name.toLowerCase().includes(searchQuery.toLowerCase()));
  }, [kbs, searchQuery]);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans selection:bg-blue-100 relative">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
      <div className="absolute left-0 right-0 top-0 h-[500px] w-full bg-gradient-to-b from-blue-100/40 via-indigo-50/20 to-transparent pointer-events-none" />

      <div className="relative z-10 flex flex-col flex-1">
        <Header />
        
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8 lg:p-10 animate-in fade-in duration-700 slide-in-from-bottom-4">
          
          {/* Header Section */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-xs font-semibold tracking-wide border border-indigo-100/50 shadow-sm">
                  <Building2 className="w-3.5 h-3.5" />
                  {user.email}
                </span>
              </div>
              <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-slate-900 via-blue-800 to-indigo-900 mb-3">
                Knowledge Bases
              </h1>
              <p className="text-slate-500 text-base md:text-lg max-w-2xl leading-relaxed">
                Manage and organize your company's intelligence. Create isolated repositories to power your AI assistants.
              </p>
            </div>
            
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              {/* @ts-ignore */}
              <DialogTrigger asChild>
                <Button className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-500/25 transition-all hover:scale-105 active:scale-95 h-12 px-6 rounded-xl font-medium text-base">
                  <Plus className="mr-2 h-5 w-5" />
                  New Repository
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[460px] p-0 overflow-hidden border-slate-200/60 shadow-2xl rounded-2xl">
                <div className="px-6 py-6 bg-gradient-to-b from-blue-50/80 to-white border-b border-slate-100">
                  <DialogHeader>
                    <DialogTitle className="text-xl font-semibold flex items-center gap-2 text-slate-800">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <Database className="w-5 h-5 text-blue-600" />
                      </div>
                      Create Repository
                    </DialogTitle>
                  </DialogHeader>
                  <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                    Set up a dedicated space for specific documents or domains to feed your RAG pipeline.
                  </p>
                </div>
                
                <form onSubmit={handleCreateKb}>
                  <div className="p-6 bg-white">
                    <div className="space-y-4">
                      <label htmlFor="name" className="text-sm font-semibold text-slate-700 block">
                        Repository Name
                      </label>
                      <Input
                        id="name"
                        placeholder="e.g. Q3 Financial Reports, HR Policies..."
                        value={newKbName}
                        onChange={(e) => setNewKbName(e.target.value)}
                        className="h-12 focus-visible:ring-blue-500/30 text-base rounded-xl bg-slate-50/50"
                        required
                        autoFocus
                      />
                      <div className="p-3 bg-blue-50/50 rounded-lg border border-blue-100/50">
                        <p className="text-xs text-blue-800/80 leading-relaxed">
                          <span className="font-semibold">Note:</span> The name will be automatically converted into a unique lowercase identifier for backend integration.
                        </p>
                      </div>
                    </div>
                  </div>
                  <DialogFooter className="px-6 py-4 bg-slate-50/80 border-t border-slate-100">
                    <Button type="button" variant="ghost" onClick={() => setIsDialogOpen(false)} disabled={isCreating} className="rounded-xl">
                      Cancel
                    </Button>
                    <Button type="submit" className="bg-blue-600 hover:bg-blue-700 min-w-[120px] rounded-xl shadow-md" disabled={!newKbName.trim() || isCreating}>
                      {isCreating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                      {isCreating ? "Creating..." : "Create"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {/* Search and Filters bar */}
          {!isLoading && kbs.length > 0 && (
            <div className="flex items-center gap-4 mb-8">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input 
                  placeholder="Search repositories..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 h-11 bg-white border-slate-200/80 shadow-sm rounded-xl focus-visible:ring-indigo-500/20 focus-visible:border-indigo-400 transition-all"
                />
              </div>
            </div>
          )}

          {/* Main Content Area */}
          {isLoading ? (
            <div className="py-32 flex flex-col items-center justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-500 blur-xl opacity-20 rounded-full animate-pulse" />
                <Loader2 className="w-10 h-10 text-blue-600 animate-spin relative z-10" />
              </div>
              <p className="text-slate-500 text-sm font-medium mt-6 animate-pulse">Synchronizing with AWS...</p>
            </div>
          ) : kbs.length === 0 ? (
            <div className="text-center py-28 bg-white/40 backdrop-blur-md rounded-3xl border border-dashed border-slate-300 shadow-sm">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-inner border border-blue-100/60">
                <FolderOpen className="h-10 w-10 text-blue-500" />
              </div>
              <h3 className="text-2xl font-bold text-slate-800">No Repositories Found</h3>
              <p className="mt-3 text-base text-slate-500 max-w-md mx-auto leading-relaxed">
                Your workspace is completely empty. Create your first knowledge base to unlock the power of RAG AI.
              </p>
              <Button onClick={() => setIsDialogOpen(true)} className="mt-8 bg-white hover:bg-slate-50 text-blue-600 border-blue-200 shadow-sm h-12 px-6 rounded-xl font-medium" variant="outline">
                <Plus className="mr-2 h-5 w-5" /> Initialize Workspace
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredKbs.map((kb, index) => (
                <div 
                  key={kb.id} 
                  className="animate-in fade-in slide-in-from-bottom-4 fill-mode-both"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <Card
                    className="group h-full flex flex-col bg-white/80 backdrop-blur-xl border-slate-200/60 shadow-sm hover:shadow-xl hover:shadow-blue-900/5 hover:-translate-y-1.5 hover:border-blue-300 transition-all duration-300 overflow-hidden cursor-pointer relative rounded-2xl"
                    onClick={() => navigate(`/kb?kb_id=${kb.id}`)}
                  >
                    <CardHeader className="pb-4">
                      <div className="flex items-start justify-between mb-4">
                        <div className="p-3 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl group-hover:from-blue-100 group-hover:to-indigo-100 group-hover:scale-110 transition-all duration-300 border border-blue-100/50 shadow-inner">
                          <Database className="w-6 h-6 text-blue-600 group-hover:text-blue-700" />
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(kb.id); }}
                            className="opacity-0 group-hover:opacity-100 transition-all duration-300 p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 focus:opacity-100"
                            title="Delete workspace"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      <CardTitle className="text-xl font-bold text-slate-800 line-clamp-1 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-blue-700 group-hover:to-indigo-700 transition-all" title={kb.name}>
                        {kb.name}
                      </CardTitle>
                      <p className="text-xs text-slate-400 font-mono truncate mt-1">
                        ID: {kb.id}
                      </p>
                    </CardHeader>
                    
                    <CardContent className="flex-1 pb-5 pt-0 mt-auto">
                      <div className="flex items-center justify-between border-t border-slate-100 pt-4 mt-2">
                        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
                          <Calendar className="w-4 h-4 text-slate-400" />
                          {kb.createdAt}
                        </div>
                        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-50 text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                          <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                        </div>
                      </div>
                    </CardContent>
                    
                    {/* Bottom Gradient Bar */}
                    <div className="h-1.5 w-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300 absolute bottom-0 left-0" />
                  </Card>
                </div>
              ))}
              
              {filteredKbs.length === 0 && searchQuery && (
                <div className="col-span-full py-20 text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-slate-100 mb-4">
                    <Search className="w-6 h-6 text-slate-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-700">No matching repositories</h3>
                  <p className="text-slate-500 mt-1">Try adjusting your search query.</p>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Confirm Delete Dialog */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 p-7 max-w-sm w-full mx-4 animate-in zoom-in-95 duration-200">
            <div className="flex items-center gap-4 mb-5">
              <div className="p-3 bg-red-50 rounded-2xl border border-red-100">
                <Trash2 className="w-6 h-6 text-red-500" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Delete Repository?</h3>
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-8 leading-relaxed">
              This will permanently delete <span className="font-bold text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded">{confirmDeleteId}</span> and all its connected documents. <span className="text-red-500 font-medium">This action cannot be undone.</span>
            </p>
            <div className="flex gap-3 justify-end">
              <Button variant="ghost" onClick={() => setConfirmDeleteId(null)} disabled={!!deletingId} className="rounded-xl h-11 px-5">
                Cancel
              </Button>
              <Button
                className="bg-red-500 hover:bg-red-600 text-white rounded-xl h-11 px-6 shadow-md shadow-red-500/20"
                onClick={() => handleDeleteKb(confirmDeleteId)}
                disabled={!!deletingId}
              >
                {deletingId === confirmDeleteId ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                {deletingId === confirmDeleteId ? 'Deleting...' : 'Delete Permanently'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
