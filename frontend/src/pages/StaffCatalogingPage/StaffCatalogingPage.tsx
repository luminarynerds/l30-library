/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AdminShell } from '../../components/shells/AdminShell'
import BulkOperationsPanel from "../../components/staff/BulkOperationsPanel"
import { Search, Plus, Loader2 } from "lucide-react"
import ConfirmDialog from '../../components/ConfirmDialog'
import { useStaffCataloging } from "./useStaffCataloging"
import CatalogResultsTable from "./CatalogResultsTable"
import CatalogItemFormModal from "./CatalogItemFormModal"
import BulkActionModal from "./BulkActionModal"
import CatalogQueuePanel from "./CatalogQueuePanel"
import CsvImportExportPanel from "./CsvImportExportPanel"
import { t } from '@/i18n'
import { Link } from 'react-router-dom'

export default function StaffCatalogingPage(): React.ReactElement {
  const cataloging = useStaffCataloging()

  if (cataloging.authLoading) return <div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>
  if (!cataloging.user || cataloging.user.role === "patron") return <></>

  return (
    <AdminShell title="Catalog Management" subtitle="Add, edit, and manage library items">
          <div className="flex items-center justify-between">
            <CsvImportExportPanel
              searchResults={cataloging.searchResults}
              token={cataloging.token}
              onImportComplete={() => cataloging.handleSearch(1)}
            />
            <Link to="/staff/cataloging/lexile-import" className="text-sm text-lsc-rose underline">{t('staff_lexile_bulk_link')}</Link>
            <button onClick={cataloging.openAddForm} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors">
              <Plus aria-hidden="true" className="w-4 h-4" />Add Item
            </button>
          </div>

          {/* Workflow Status */}
          <CatalogQueuePanel
            activeStatus={cataloging.catalogingStatusFilter}
            onStatusClick={cataloging.setCatalogingStatusFilter}
            onWorkNext={cataloging.handleWorkNext}
            statsRefreshKey={cataloging.statsRefreshKey}
          />

          {/* Search */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
            <form onSubmit={cataloging.handleSearchSubmit} className="flex gap-2">
              <input type="text" value={cataloging.searchQuery} onChange={(e) => cataloging.setSearchQuery(e.target.value)}
                placeholder={t('placeholder.staffCataloging.searchByTitleAuthor')}
                aria-label={t('aria.staffCataloging.searchByTitleAuthorIsbn')}
                className="flex-1 px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:outline-none" />
              <button type="submit" disabled={cataloging.isSearching}
                className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium flex items-center gap-2 transition-colors">
                {cataloging.isSearching ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search aria-hidden="true" className="w-4 h-4" />}
                Search
              </button>
            </form>
          </div>

          {/* Bulk Operations */}
          {cataloging.searchResults && cataloging.searchResults.items.length > 0 && (
            <BulkOperationsPanel
              selectedIds={cataloging.selectedIds}
              totalItems={cataloging.searchResults.total}
              actions={cataloging.bulkActions}
              onSelectionChange={cataloging.setSelectedIds}
              allItemIds={cataloging.searchResults.items.map(item => item.id)}
              pageItemIds={cataloging.searchResults.items.map(item => item.id)}
              itemLabel="items"
              showSelectionBadge={true}
            />
          )}

          {/* Results Table */}
          <CatalogResultsTable
            searchResults={cataloging.searchResults}
            currentPage={cataloging.currentPage}
            isSearching={cataloging.isSearching}
            selectedCount={cataloging.selectedCount}
            isSelected={cataloging.isSelected}
            toggleSelection={cataloging.toggleSelection}
            setSelectedIds={cataloging.setSelectedIds}
            onEdit={cataloging.openEditForm}
            onDelete={cataloging.setDeleteConfirm}
            onPageChange={(page) => cataloging.handleSearch(page)}
          />

      {/* Add/Edit Form Modal */}
      <CatalogItemFormModal
        isOpen={cataloging.showAddForm}
        editingItem={cataloging.editingItem}
        formData={cataloging.formData}
        setFormData={cataloging.setFormData}
        onFormChange={cataloging.handleFormChange}
        onSubmit={cataloging.handleSubmit}
        onSaveAndAddAnother={cataloging.handleSubmitKeepOpen}
        recentItems={cataloging.searchResults?.items ?? []}
        onClose={cataloging.closeForm}
        isSaving={cataloging.isSaving}
        onGenerateBarcode={cataloging.handleGenerateBarcode}
        duplicates={cataloging.duplicates}
        isCheckingDuplicates={cataloging.isCheckingDuplicates}
        showDuplicateWarning={cataloging.showDuplicateWarning}
        draftRestored={cataloging.draftRestored}
        setDraftRestored={cataloging.setDraftRestored}
        showZ3950Search={cataloging.showZ3950Search}
        setShowZ3950Search={cataloging.setShowZ3950Search}
        z3950Results={cataloging.z3950Results}
        isSearchingZ3950={cataloging.isSearchingZ3950}
        onZ3950Search={cataloging.handleZ3950Search}
        onZ3950Import={cataloging.importZ3950Record}
        selectedZ3950Record={cataloging.selectedZ3950Record}
        onSelectZ3950Record={cataloging.selectZ3950Record}
        onUseZ3950Field={cataloging.useZ3950Field}
        onUseAllZ3950Data={cataloging.useAllZ3950Data}
        onClearZ3950Selection={cataloging.clearZ3950Selection}
        isFetchingCover={cataloging.isFetchingCover}
        onFetchCover={cataloging.handleFetchCover}
        catalogImages={cataloging.catalogImages}
        onImagesChanged={cataloging.handleImagesChanged}
        isStale={cataloging.isStale}
        conflictData={cataloging.conflictData}
        onForceSave={cataloging.onForceSave}
        onReloadItem={cataloging.onReloadItem}
        onCancelConflict={cataloging.onCancelConflict}
        hasRationale={cataloging.hasRationale}
        setHasRationale={cataloging.setHasRationale}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!cataloging.deleteConfirm}
        title="Delete Item"
        message={`Delete "${cataloging.deleteConfirm?.title}"? This cannot be undone.`}
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={cataloging.handleDelete}
        onCancel={() => cataloging.setDeleteConfirm(null)}
        loading={cataloging.isDeleting}
      />

      {/* Bulk Action Modal */}
      {cataloging.bulkModal && (
        <BulkActionModal
          modal={cataloging.bulkModal}
          value={cataloging.bulkModalValue}
          onChange={cataloging.setBulkModalValue}
          onSubmit={cataloging.handleBulkModalSubmit}
          onCancel={() => { cataloging.setBulkModal(null); cataloging.setBulkModalValue("") }}
          isUpdating={cataloging.isBulkUpdating}
        />
      )}
    </AdminShell>
  )
}
