import { useEffect, useState, type FormEvent } from "react";
import {
  createUser,
  fetchUsers,
  resetUserMfa,
  resetUserPassword,
  restartUserWalkthrough,
  updateUser,
  type CurrentUser,
} from "../api/security";
import { cn } from "../utils/cn";

const USER_ROLES = ["Admin", "UR", "Read Only"];

interface AdminUsersPageProps {
  darkMode: boolean;
  currentUser: CurrentUser;
}

interface NewUserForm {
  username: string;
  role: string;
}

const emptyUserForm: NewUserForm = {
  username: "",
  role: "UR",
};

export function AdminUsersPage({ darkMode, currentUser }: AdminUsersPageProps) {
  const [users, setUsers] = useState<CurrentUser[]>([]);
  const [newUserForm, setNewUserForm] = useState<NewUserForm>(emptyUserForm);
  const [isLoadingUsers, setIsLoadingUsers] = useState(true);
  const [isSavingUser, setIsSavingUser] = useState(false);
  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null);
  const [resettingUserId, setResettingUserId] = useState<number | null>(null);
  const [resettingMfaUserId, setResettingMfaUserId] = useState<number | null>(
    null
  );
  const [restartingWalkthroughUserId, setRestartingWalkthroughUserId] =
    useState<number | null>(null);
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(
    null
  );
  const [temporaryPasswordUsername, setTemporaryPasswordUsername] = useState<
    string | null
  >(null);
  const [hasCopiedTemporaryPassword, setHasCopiedTemporaryPassword] =
    useState(false);
  const [usersError, setUsersError] = useState<string | null>(null);

  async function loadUsers() {
    setIsLoadingUsers(true);
    setUsersError(null);

    try {
      const loadedUsers = await fetchUsers();
      setUsers(loadedUsers);
    } catch (error) {
      setUsersError(
        error instanceof Error ? error.message : "Unable to load users."
      );
    } finally {
      setIsLoadingUsers(false);
    }
  }

  useEffect(() => {
    void loadUsers();
  }, []);

  const handleCreateUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSavingUser(true);
    setUsersError(null);
    setTemporaryPassword(null);
    setTemporaryPasswordUsername(null);
    setHasCopiedTemporaryPassword(false);

    try {
      const result = await createUser({
        username: newUserForm.username,
        role: newUserForm.role,
      });

      setUsers((currentUsers) =>
        [...currentUsers, result.user].sort((firstUser, secondUser) =>
          firstUser.username.localeCompare(secondUser.username)
        )
      );

      setTemporaryPassword(result.temporary_password);
      setTemporaryPasswordUsername(result.user.username);
      setHasCopiedTemporaryPassword(false);
      setNewUserForm(emptyUserForm);
    } catch (error) {
      setUsersError(
        error instanceof Error ? error.message : "Unable to create user."
      );
    } finally {
      setIsSavingUser(false);
    }
  };

  const handleUpdateUser = async (
    user: CurrentUser,
    payload: { role?: string; is_active?: boolean }
  ) => {
    setUpdatingUserId(user.id);
    setUsersError(null);

    try {
      const updatedUser = await updateUser(user.id, payload);

      setUsers((currentUsers) =>
        currentUsers.map((currentUserItem) =>
          currentUserItem.id === updatedUser.id ? updatedUser : currentUserItem
        )
      );
    } catch (error) {
      setUsersError(
        error instanceof Error ? error.message : "Unable to update user."
      );
    } finally {
      setUpdatingUserId(null);
    }
  };

  const handleResetPassword = async (user: CurrentUser) => {
    const confirmed = window.confirm(
      `Reset the password for ${user.username}? This will immediately revoke all of their active sessions.`
    );

    if (!confirmed) {
      return;
    }

    setResettingUserId(user.id);
    setUsersError(null);
    setTemporaryPassword(null);
    setTemporaryPasswordUsername(null);
    setHasCopiedTemporaryPassword(false);

    try {
      const result = await resetUserPassword(user.id);

      setUsers((currentUsers) =>
        currentUsers.map((currentUserItem) =>
          currentUserItem.id === user.id
            ? {
                ...currentUserItem,
                must_change_password: result.must_change_password,
              }
            : currentUserItem
        )
      );

      setTemporaryPassword(result.temporary_password);
      setTemporaryPasswordUsername(user.username);
    } catch (error) {
      setUsersError(
        error instanceof Error ? error.message : "Unable to reset password."
      );
    } finally {
      setResettingUserId(null);
    }
  };

  const handleResetMfa = async (user: CurrentUser) => {
    const confirmed = window.confirm(
      `Reset MFA for ${user.username}? This will remove their authenticator setup and immediately revoke all of their active sessions. They will need to enroll MFA again.`
    );

    if (!confirmed) {
      return;
    }

    setResettingMfaUserId(user.id);
    setUsersError(null);

    try {
      const result = await resetUserMfa(user.id);

      setUsers((currentUsers) =>
        currentUsers.map((currentUserItem) =>
          currentUserItem.id === user.id
            ? {
                ...currentUserItem,
                mfa_enabled: result.mfa_enabled,
              }
            : currentUserItem
        )
      );
    } catch (error) {
      setUsersError(
        error instanceof Error ? error.message : "Unable to reset MFA."
      );
    } finally {
      setResettingMfaUserId(null);
    }
  };

  const handleRestartWalkthrough = async (user: CurrentUser) => {
    const confirmed = window.confirm(
      `Restart the walkthrough for ${user.username}? This only resets their walkthrough progress and does not remove application data.`
    );

    if (!confirmed) {
      return;
    }

    setRestartingWalkthroughUserId(user.id);
    setUsersError(null);

    try {
      const result = await restartUserWalkthrough(user.id);

      setUsers((currentUsers) =>
        currentUsers.map((currentUserItem) =>
          currentUserItem.id === user.id
            ? {
                ...currentUserItem,
                walkthrough_status: result.walkthrough_status,
              }
            : currentUserItem
        )
      );
    } catch (error) {
      setUsersError(
        error instanceof Error
          ? error.message
          : "Unable to restart walkthrough."
      );
    } finally {
      setRestartingWalkthroughUserId(null);
    }
  };

  const handleCopyTemporaryPassword = async () => {
    if (!temporaryPassword) {
      return;
    }

    try {
      await navigator.clipboard.writeText(temporaryPassword);
      setHasCopiedTemporaryPassword(true);
    } catch {
      setUsersError(
        "Unable to copy the temporary password. Select and copy it manually."
      );
    }
  };

  return (
    <div className="space-y-6">
      {temporaryPassword && temporaryPasswordUsername && (
        <section
          className={cn(
            "rounded-xl border p-6 shadow-sm",
            darkMode
              ? "border-amber-800 bg-amber-950/30"
              : "border-amber-200 bg-amber-50"
          )}
        >
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-lg font-semibold">
                Temporary password ready
              </h2>

              <p
                className={cn(
                  "mt-1 text-sm",
                  darkMode ? "text-amber-200" : "text-amber-800"
                )}
              >
                Give this password securely to {temporaryPasswordUsername}. It
                will not be available again after this panel is dismissed or the
                page is refreshed.
              </p>

              <p
                className={cn(
                  "mt-2 text-sm",
                  darkMode ? "text-gray-300" : "text-gray-700"
                )}
              >
                The user must change it after signing in. Any previous active
                sessions have been revoked.
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setTemporaryPassword(null);
                setTemporaryPasswordUsername(null);
                setHasCopiedTemporaryPassword(false);
              }}
              className={cn(
                "self-start rounded-lg border px-3 py-2 text-sm font-medium",
                darkMode
                  ? "border-gray-700 text-gray-200 hover:bg-gray-800"
                  : "border-gray-300 text-gray-700 hover:bg-white"
              )}
            >
              Dismiss
            </button>
          </div>

          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              readOnly
              value={temporaryPassword}
              aria-label={`Temporary password for ${temporaryPasswordUsername}`}
              className={cn(
                "min-w-0 flex-1 rounded-lg border px-3 py-2 font-mono text-sm",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
              onFocus={(event) => event.currentTarget.select()}
            />

            <button
              type="button"
              onClick={() => void handleCopyTemporaryPassword()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              {hasCopiedTemporaryPassword ? "Copied" : "Copy password"}
            </button>
          </div>
        </section>
      )}
      <section
        className={cn(
          "rounded-xl border p-6 shadow-sm",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <div>
          <h2 className="text-lg font-semibold">Create user</h2>
          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Create local CareQFlow users. A secure temporary password will be
            generated automatically.
          </p>
        </div>

        <form
          onSubmit={handleCreateUser}
          className="mt-6 grid gap-4 lg:grid-cols-[1fr_220px_auto]"
        >
          <label className="space-y-2">
            <span className="text-sm font-medium">Username</span>
            <input
              type="email"
              autoComplete="username"
              value={newUserForm.username}
              onChange={(event) =>
                setNewUserForm((currentForm) => ({
                  ...currentForm,
                  username: event.target.value,
                }))
              }
              required
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm outline-none",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
            />
          </label>

          <label className="space-y-2">
            <span className="text-sm font-medium">Role</span>
            <select
              value={newUserForm.role}
              onChange={(event) =>
                setNewUserForm((currentForm) => ({
                  ...currentForm,
                  role: event.target.value,
                }))
              }
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm outline-none",
                darkMode
                  ? "border-gray-700 bg-gray-950 text-gray-100"
                  : "border-gray-300 bg-white text-gray-900"
              )}
            >
              {USER_ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={isSavingUser}
              className={cn(
                "rounded-lg px-4 py-2 text-sm font-medium text-white",
                isSavingUser ? "bg-blue-400" : "bg-blue-600 hover:bg-blue-700"
              )}
            >
              {isSavingUser ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </section>

      <section
        className={cn(
          "rounded-xl border shadow-sm",
          darkMode ? "border-gray-800 bg-gray-900" : "border-gray-200 bg-white"
        )}
      >
        <div className="border-b border-inherit p-6">
          <h2 className="text-lg font-semibold">Users</h2>
          <p
            className={cn(
              "mt-1 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Manage local users, roles, and active status.
          </p>
        </div>

        {usersError && (
          <div
            className={cn(
              "mx-6 mt-4 rounded-lg border px-4 py-3 text-sm",
              darkMode
                ? "border-red-900/60 bg-red-950/40 text-red-200"
                : "border-red-200 bg-red-50 text-red-700"
            )}
          >
            {usersError}
          </div>
        )}

        {isLoadingUsers ? (
          <div
            className={cn(
              "p-6 text-sm",
              darkMode ? "text-gray-400" : "text-gray-600"
            )}
          >
            Loading users...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead
                className={cn(
                  "border-b",
                  darkMode
                    ? "border-gray-800 text-gray-400"
                    : "border-gray-200 text-gray-600"
                )}
              >
                <tr>
                  <th className="px-6 py-3 font-medium">Username</th>
                  <th className="px-6 py-3 font-medium">Role</th>
                  <th className="px-6 py-3 font-medium">Status / MFA</th>
                  <th className="px-6 py-3 font-medium">Last login</th>
                  <th className="px-6 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => {
                  const isCurrentUser = user.id === currentUser.id;
                  const isUpdating = updatingUserId === user.id;

                  return (
                    <tr
                      key={user.id}
                      className={cn(
                        "border-b last:border-b-0",
                        darkMode ? "border-gray-800" : "border-gray-100"
                      )}
                    >
                      <td className="px-6 py-4">
                        <div className="font-medium">{user.username}</div>
                        {isCurrentUser && (
                          <div
                            className={cn(
                              "mt-1 text-xs",
                              darkMode ? "text-blue-300" : "text-blue-600"
                            )}
                          >
                            Current user
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <select
                          value={user.role}
                          disabled={isUpdating || isCurrentUser}
                          onChange={(event) =>
                            handleUpdateUser(user, {
                              role: event.target.value,
                            })
                          }
                          className={cn(
                            "rounded-lg border px-3 py-2 text-sm outline-none",
                            darkMode
                              ? "border-gray-700 bg-gray-950 text-gray-100 disabled:text-gray-500"
                              : "border-gray-300 bg-white text-gray-900 disabled:text-gray-500"
                          )}
                        >
                          {USER_ROLES.map((role) => (
                            <option key={role} value={role}>
                              {role}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-2">
                          <span
                            className={cn(
                              "rounded-full px-2.5 py-1 text-xs font-medium",
                              user.is_active
                                ? darkMode
                                  ? "bg-green-950 text-green-300"
                                  : "bg-green-100 text-green-700"
                                : darkMode
                                ? "bg-gray-800 text-gray-400"
                                : "bg-gray-100 text-gray-600"
                            )}
                          >
                            {user.is_active ? "Active" : "Inactive"}
                          </span>

                          {user.must_change_password && (
                            <span
                              className={cn(
                                "rounded-full px-2.5 py-1 text-xs font-medium",
                                darkMode
                                  ? "bg-amber-950 text-amber-300"
                                  : "bg-amber-100 text-amber-700"
                              )}
                            >
                              Password change required
                            </span>
                          )}

                          <span
                            className={cn(
                              "rounded-full px-2.5 py-1 text-xs font-medium",
                              user.mfa_enabled
                                ? darkMode
                                  ? "bg-blue-950 text-blue-300"
                                  : "bg-blue-100 text-blue-700"
                                : darkMode
                                ? "bg-gray-800 text-gray-400"
                                : "bg-gray-100 text-gray-600"
                            )}
                          >
                            {user.mfa_enabled
                              ? "MFA enabled"
                              : "MFA not enabled"}
                          </span>
                          <span
                            className={cn(
                              "rounded-full px-2.5 py-1 text-xs font-medium",
                              user.walkthrough_status === "pending"
                                ? darkMode
                                  ? "bg-amber-950 text-amber-300"
                                  : "bg-amber-100 text-amber-700"
                                : user.walkthrough_status === "completed"
                                ? darkMode
                                  ? "bg-green-950 text-green-300"
                                  : "bg-green-100 text-green-700"
                                : darkMode
                                ? "bg-gray-800 text-gray-400"
                                : "bg-gray-100 text-gray-600"
                            )}
                          >
                            {user.walkthrough_status === "pending"
                              ? "Walkthrough pending"
                              : user.walkthrough_status === "completed"
                              ? "Walkthrough completed"
                              : "Walkthrough skipped"}
                          </span>
                        </div>
                      </td>
                      <td
                        className={cn(
                          "px-6 py-4",
                          darkMode ? "text-gray-400" : "text-gray-600"
                        )}
                      >
                        {user.last_login_at ?? "Never"}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={isUpdating || isCurrentUser}
                            onClick={() =>
                              handleUpdateUser(user, {
                                is_active: !user.is_active,
                              })
                            }
                            className={cn(
                              "rounded-lg px-3 py-2 text-sm font-medium",
                              user.is_active
                                ? darkMode
                                  ? "bg-gray-800 text-gray-200 hover:bg-gray-700"
                                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                : "bg-blue-600 text-white hover:bg-blue-700",
                              (isUpdating || isCurrentUser) &&
                                "cursor-not-allowed opacity-50"
                            )}
                          >
                            {user.is_active ? "Deactivate" : "Activate"}
                          </button>

                          <button
                            type="button"
                            disabled={
                              isUpdating ||
                              resettingUserId !== null ||
                              resettingMfaUserId !== null ||
                              isCurrentUser ||
                              !user.is_active
                            }
                            onClick={() => void handleResetPassword(user)}
                            className={cn(
                              "rounded-lg border px-3 py-2 text-sm font-medium",
                              darkMode
                                ? "border-gray-700 text-gray-200 hover:bg-gray-800"
                                : "border-gray-300 text-gray-700 hover:bg-gray-100",
                              (isUpdating ||
                                resettingUserId !== null ||
                                resettingMfaUserId !== null ||
                                isCurrentUser ||
                                !user.is_active) &&
                                "cursor-not-allowed opacity-50"
                            )}
                          >
                            {resettingUserId === user.id
                              ? "Resetting..."
                              : "Reset password"}
                          </button>

                          <button
                            type="button"
                            disabled={
                              isUpdating ||
                              resettingUserId !== null ||
                              resettingMfaUserId !== null ||
                              isCurrentUser ||
                              !user.is_active ||
                              !user.mfa_enabled
                            }
                            onClick={() => void handleResetMfa(user)}
                            className={cn(
                              "rounded-lg border px-3 py-2 text-sm font-medium",
                              darkMode
                                ? "border-gray-700 text-gray-200 hover:bg-gray-800"
                                : "border-gray-300 text-gray-700 hover:bg-gray-100",
                              (isUpdating ||
                                resettingUserId !== null ||
                                resettingMfaUserId !== null ||
                                isCurrentUser ||
                                !user.is_active ||
                                !user.mfa_enabled) &&
                                "cursor-not-allowed opacity-50"
                            )}
                          >
                            {resettingMfaUserId === user.id
                              ? "Resetting MFA..."
                              : "Reset MFA"}
                          </button>
                          <button
                            type="button"
                            disabled={
                              isUpdating ||
                              resettingUserId !== null ||
                              resettingMfaUserId !== null ||
                              restartingWalkthroughUserId !== null ||
                              !user.is_active ||
                              user.walkthrough_status === "pending"
                            }
                            onClick={() => void handleRestartWalkthrough(user)}
                            className={cn(
                              "rounded-lg border px-3 py-2 text-sm font-medium",
                              darkMode
                                ? "border-gray-700 text-gray-200 hover:bg-gray-800"
                                : "border-gray-300 text-gray-700 hover:bg-gray-100",
                              (isUpdating ||
                                resettingUserId !== null ||
                                resettingMfaUserId !== null ||
                                restartingWalkthroughUserId !== null ||
                                !user.is_active ||
                                user.walkthrough_status === "pending") &&
                                "cursor-not-allowed opacity-50"
                            )}
                          >
                            {restartingWalkthroughUserId === user.id
                              ? "Restarting..."
                              : "Restart walkthrough"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {users.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className={cn(
                        "px-6 py-8 text-center text-sm",
                        darkMode ? "text-gray-400" : "text-gray-600"
                      )}
                    >
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
