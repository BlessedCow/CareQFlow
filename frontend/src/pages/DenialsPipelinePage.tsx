import type { AuthRequest } from "../types/auth";
import { cn } from "../utils/cn";
import { FollowUpDashboard } from "./denialsPipeline/FollowUpDashboard";
import { FollowUpFormSections } from "./denialsPipeline/FollowUpFormSections";
import { SelectedAuthorizationBanner } from "./denialsPipeline/SelectedAuthorizationBanner";
import { getFollowUpItems } from "./denialsPipeline/followUpModels";
import { useFollowUpForms } from "./denialsPipeline/useFollowUpForms";

interface DenialsPipelinePageProps {
  data: AuthRequest[];
  darkMode: boolean;
  selectedAuthId: string | null;
  canManageAuthorizations: boolean;
  onSelectAuth: (auth: AuthRequest) => void;
  onClearSelectedAuth: () => void;
  onAuthUpdated: (auth: AuthRequest) => void;
}

export function DenialsPipelinePage({
  data,
  darkMode,
  selectedAuthId,
  canManageAuthorizations,
  onSelectAuth,
  onClearSelectedAuth,
  onAuthUpdated,
}: DenialsPipelinePageProps) {
  const selectedAuth = selectedAuthId
    ? data.find((auth) => auth.id === selectedAuthId) ?? null
    : null;
  const followUpItems = getFollowUpItems(data);

  const {
    denialForm,
    denialError,
    isSavingDenial,
    p2pForm,
    p2pError,
    isSavingP2P,
    appealForm,
    appealError,
    isSavingAppeal,
    retroForm,
    retroError,
    isSavingRetro,
    handleDenialFieldChange,
    handleP2PFieldChange,
    handleAppealFieldChange,
    handleRetroFieldChange,
    handleSaveDenial,
    handleSaveP2P,
    handleSaveAppeal,
    handleSaveRetro,
    handleClearDenial,
    handleClearP2P,
    handleClearAppeal,
    handleClearRetro,
  } = useFollowUpForms({ selectedAuth, onAuthUpdated });
  return (
    <div className="h-full overflow-auto p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold">Denials / P2P / Retro</h2>
        <p
          className={cn(
            "mt-1 text-sm",
            darkMode ? "text-gray-400" : "text-gray-600"
          )}
        >
          Focused workspace for denial follow-up, peer reviews, appeals, and
          retro authorization work.
        </p>
      </div>

      <FollowUpDashboard
        data={data}
        darkMode={darkMode}
        selectedAuth={selectedAuth}
        followUpItems={followUpItems}
        onSelectAuth={onSelectAuth}
      />

      {selectedAuth && (
        <SelectedAuthorizationBanner
          selectedAuth={selectedAuth}
          darkMode={darkMode}
        />
      )}

      <FollowUpFormSections
        selectedAuth={selectedAuth}
        darkMode={darkMode}
        canManageAuthorizations={canManageAuthorizations}
        denialForm={denialForm}
        denialError={denialError}
        isSavingDenial={isSavingDenial}
        p2pForm={p2pForm}
        p2pError={p2pError}
        isSavingP2P={isSavingP2P}
        appealForm={appealForm}
        appealError={appealError}
        isSavingAppeal={isSavingAppeal}
        retroForm={retroForm}
        retroError={retroError}
        isSavingRetro={isSavingRetro}
        onClearSelectedAuth={onClearSelectedAuth}
        onDenialFieldChange={handleDenialFieldChange}
        onP2PFieldChange={handleP2PFieldChange}
        onAppealFieldChange={handleAppealFieldChange}
        onRetroFieldChange={handleRetroFieldChange}
        onSaveDenial={handleSaveDenial}
        onSaveP2P={handleSaveP2P}
        onSaveAppeal={handleSaveAppeal}
        onSaveRetro={handleSaveRetro}
        onClearDenial={handleClearDenial}
        onClearP2P={handleClearP2P}
        onClearAppeal={handleClearAppeal}
        onClearRetro={handleClearRetro}
      />
    </div>
  );
}
