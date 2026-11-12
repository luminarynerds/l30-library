/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  listTags,
  createTag,
  updateTag,
  deleteTag,
  listGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  getGroupDetail,
  getGroupStats,
  sendGroupMessage,
  exportGroupMembers,
  TAG_COLORS,
  type Tag,
  type PatronGroup,
  type GroupDetail,
  type GroupStats,
} from "../api/patron-segmentation-api"
import {
  Tags,
  Users,
  Plus,
  Loader2,
  Search,
  RefreshCw,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { TagsView } from "../components/patron-segmentation/TagsView"
import { GroupsView } from "../components/patron-segmentation/GroupsView"
import { TagModal } from "../components/patron-segmentation/TagModal"
import { GroupModal } from "../components/patron-segmentation/GroupModal"
import { MessageModal } from "../components/patron-segmentation/MessageModal"
import { DeleteConfirmModal } from "../components/patron-segmentation/DeleteConfirmModal"

type ViewMode = "tags" | "groups"
type ModalType = "tag" | "group" | "message" | null

export default function StaffPatronSegmentationPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [viewMode, setViewMode] = useState<ViewMode>("tags")
  const [isLoading, setIsLoading] = useState(true)

  const [tags, setTags] = useState<Tag[]>([])
  const [tagSearch, setTagSearch] = useState("")
  const [includeInactiveTags, setIncludeInactiveTags] = useState(false)

  const [groups, setGroups] = useState<PatronGroup[]>([])
  const [groupSearch, setGroupSearch] = useState("")
  const [includeInactiveGroups, setIncludeInactiveGroups] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<GroupDetail | null>(null)
  const [groupStats, setGroupStats] = useState<GroupStats | null>(null)

  const [modalType, setModalType] = useState<ModalType>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const [tagForm, setTagForm] = useState({
    id: 0, name: "", color: "blue", description: "", is_active: true,
  })

  const [groupForm, setGroupForm] = useState({
    id: 0, name: "", description: "", allow_self_join: false, max_members: null as number | null, is_active: true,
  })

  const [messageForm, setMessageForm] = useState({ subject: "", message: "" })

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deletingItem, setDeletingItem] = useState<{ type: "tag" | "group"; id: number; name: string } | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('staffPatronSegmentation.toast.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  const fetchTags = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response = await listTags(token, {
        ...(tagSearch ? { search: tagSearch } : {}),
        include_inactive: includeInactiveTags,
      })
      setTags(response.tags)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.loadTagsFailed'))
    } finally {
      setIsLoading(false)
    }
  }, [token, tagSearch, includeInactiveTags, t])

  const fetchGroups = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response = await listGroups(token, {
        ...(groupSearch ? { search: groupSearch } : {}),
        include_inactive: includeInactiveGroups,
      })
      setGroups(response.groups)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.loadGroupsFailed'))
    } finally {
      setIsLoading(false)
    }
  }, [token, groupSearch, includeInactiveGroups, t])

  useEffect(() => {
    if (token && isAuthenticated) {
      if (viewMode === "tags") fetchTags()
      else fetchGroups()
    }
  }, [token, isAuthenticated, viewMode, fetchTags, fetchGroups])

  const handleSaveTag = async () => {
    if (!token || !tagForm.name.trim()) {
      toast.error(t('staffPatronSegmentation.toast.nameRequired'))
      return
    }
    setIsSaving(true)
    try {
      if (isEditing) {
        await updateTag(token, tagForm.id, clean({
          name: tagForm.name.trim(),
          color: tagForm.color,
          description: tagForm.description.trim() || undefined,
          is_active: tagForm.is_active,
        }))
        toast.success(t('staffPatronSegmentation.toast.tagUpdated'))
      } else {
        await createTag(token, clean({
          name: tagForm.name.trim(),
          color: tagForm.color,
          description: tagForm.description.trim() || undefined,
        }))
        toast.success(t('staffPatronSegmentation.toast.tagCreated'))
      }
      setModalType(null)
      resetTagForm()
      fetchTags()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.saveTagFailed'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteTag = async () => {
    if (!token || !deletingItem || deletingItem.type !== "tag") return
    setIsDeleting(true)
    try {
      await deleteTag(token, deletingItem.id)
      toast.success(t('staffPatronSegmentation.toast.tagDeleted'))
      setShowDeleteConfirm(false)
      setDeletingItem(null)
      fetchTags()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.deleteTagFailed'))
    } finally {
      setIsDeleting(false)
    }
  }

  const handleSaveGroup = async () => {
    if (!token || !groupForm.name.trim()) {
      toast.error(t('staffPatronSegmentation.toast.nameRequired'))
      return
    }
    setIsSaving(true)
    try {
      if (isEditing) {
        await updateGroup(token, groupForm.id, clean({
          name: groupForm.name.trim(),
          description: groupForm.description.trim() || undefined,
          allow_self_join: groupForm.allow_self_join,
          ...(groupForm.max_members ? { max_members: groupForm.max_members } : {}),
          is_active: groupForm.is_active,
        }))
        toast.success(t('staffPatronSegmentation.toast.groupUpdated'))
      } else {
        await createGroup(token, clean({
          name: groupForm.name.trim(),
          description: groupForm.description.trim() || undefined,
          allow_self_join: groupForm.allow_self_join,
          ...(groupForm.max_members ? { max_members: groupForm.max_members } : {}),
        }))
        toast.success(t('staffPatronSegmentation.toast.groupCreated'))
      }
      setModalType(null)
      resetGroupForm()
      fetchGroups()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.saveGroupFailed'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteGroup = async () => {
    if (!token || !deletingItem || deletingItem.type !== "group") return
    setIsDeleting(true)
    try {
      await deleteGroup(token, deletingItem.id)
      toast.success(t('staffPatronSegmentation.toast.groupDeleted'))
      setShowDeleteConfirm(false)
      setDeletingItem(null)
      if (selectedGroup?.id === deletingItem.id) setSelectedGroup(null)
      fetchGroups()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.deleteGroupFailed'))
    } finally {
      setIsDeleting(false)
    }
  }

  const handleViewGroup = async (groupId: number) => {
    if (!token) return
    try {
      const detail = await getGroupDetail(token, groupId)
      setSelectedGroup(detail)
      const stats = await getGroupStats(token, groupId)
      setGroupStats(stats)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.loadGroupDetailsFailed'))
    }
  }

  const handleSendMessage = async () => {
    if (!token || !selectedGroup || !messageForm.subject.trim() || !messageForm.message.trim()) {
      toast.error(t('staffPatronSegmentation.subjectAndMessageAreRequired'))
      return
    }
    setIsSaving(true)
    try {
      const response = await sendGroupMessage(token, selectedGroup.id, {
        subject: messageForm.subject.trim(),
        message: messageForm.message.trim(),
      })
      toast.success(t('staffPatronSegmentation.toast.messageSent', { count: response.recipient_count }))
      setModalType(null)
      setMessageForm({ subject: "", message: "" })
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.sendMessageFailed'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleExportGroup = async (groupId: number) => {
    if (!token) return
    try {
      const data = await exportGroupMembers(token, groupId)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${data.group_name.replace(/\+/g, "_")}_members.json`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(t('staffPatronSegmentation.toast.membersExported'))
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPatronSegmentation.toast.exportMembersFailed'))
    }
  }

  const resetTagForm = () => {
    setTagForm({ id: 0, name: "", color: "blue", description: "", is_active: true })
    setIsEditing(false)
  }

  const resetGroupForm = () => {
    setGroupForm({ id: 0, name: "", description: "", allow_self_join: false, max_members: null, is_active: true })
    setIsEditing(false)
  }

  const openEditTag = (tag: Tag) => {
    setTagForm({ id: tag.id, name: tag.name, color: tag.color, description: tag.description || "", is_active: tag.is_active })
    setIsEditing(true)
    setModalType("tag")
  }

  const openEditGroup = (group: PatronGroup) => {
    setGroupForm({ id: group.id, name: group.name, description: group.description || "", allow_self_join: group.allow_self_join, max_members: group.max_members, is_active: group.is_active })
    setIsEditing(true)
    setModalType("group")
  }

  void TAG_COLORS

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === "patron") return <></>

  return (
    <AdminShell title="Patron Segmentation">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Patron Segmentation
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Manage patron tags and groups for targeted communication
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => viewMode === "tags" ? fetchTags() : fetchGroups()}
            className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => {
              if (viewMode === "tags") { resetTagForm(); setModalType("tag") }
              else { resetGroupForm(); setModalType("group") }
            }}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New {viewMode === "tags" ? "Tag" : "Group"}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl w-fit">
        <button
          onClick={() => setViewMode("tags")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            viewMode === "tags"
              ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
              : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          }`}
        >
          <Tags className="w-4 h-4" />
          Tags
        </button>
        <button
          onClick={() => setViewMode("groups")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            viewMode === "groups"
              ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
              : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          }`}
        >
          <Users className="w-4 h-4" />
          Groups
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[200px] max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            placeholder={`Search ${viewMode}...`}
            value={viewMode === "tags" ? tagSearch : groupSearch}
            onChange={(e) => viewMode === "tags" ? setTagSearch(e.target.value) : setGroupSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <input
            type="checkbox"
            checked={viewMode === "tags" ? includeInactiveTags : includeInactiveGroups}
            onChange={(e) => viewMode === "tags" ? setIncludeInactiveTags(e.target.checked) : setIncludeInactiveGroups(e.target.checked)}
            className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
          />
          Show inactive
        </label>
      </div>

      {viewMode === "tags" ? (
        <TagsView
          tags={tags}
          onCreateTag={() => { resetTagForm(); setModalType("tag") }}
          onEditTag={openEditTag}
          onDeleteTag={(tag) => { setDeletingItem({ type: "tag", id: tag.id, name: tag.name }); setShowDeleteConfirm(true) }}
        />
      ) : (
        <GroupsView
          groups={groups}
          selectedGroup={selectedGroup}
          groupStats={groupStats}
          onCreateGroup={() => { resetGroupForm(); setModalType("group") }}
          onViewGroup={handleViewGroup}
          onEditGroup={openEditGroup}
          onSendMessage={() => setModalType("message")}
          onExportGroup={handleExportGroup}
          onDeleteGroup={(group) => { setDeletingItem({ type: "group", id: group.id, name: group.name }); setShowDeleteConfirm(true) }}
        />
      )}

      {modalType === "tag" && (
        <TagModal
          form={tagForm}
          onChange={setTagForm}
          isEditing={isEditing}
          isSaving={isSaving}
          onSave={handleSaveTag}
          onClose={() => { setModalType(null); resetTagForm() }}
        />
      )}

      {modalType === "group" && (
        <GroupModal
          form={groupForm}
          onChange={setGroupForm}
          isEditing={isEditing}
          isSaving={isSaving}
          onSave={handleSaveGroup}
          onClose={() => { setModalType(null); resetGroupForm() }}
        />
      )}

      {modalType === "message" && selectedGroup && (
        <MessageModal
          selectedGroup={selectedGroup}
          form={messageForm}
          onChange={setMessageForm}
          isSaving={isSaving}
          onSend={handleSendMessage}
          onClose={() => { setModalType(null); setMessageForm({ subject: "", message: "" }) }}
        />
      )}

      {showDeleteConfirm && deletingItem && (
        <DeleteConfirmModal
          deletingItem={deletingItem}
          isDeleting={isDeleting}
          onConfirm={() => deletingItem.type === "tag" ? handleDeleteTag() : handleDeleteGroup()}
          onClose={() => { setShowDeleteConfirm(false); setDeletingItem(null) }}
        />
      )}
    </AdminShell>
  )
}
