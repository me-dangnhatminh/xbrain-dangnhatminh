/**
 * Cognito Authentication Service
 *
 * Wraps amazon-cognito-identity-js to provide sign-in, sign-out,
 * and token retrieval for the DocHub AI frontend.
 */

import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
} from 'amazon-cognito-identity-js';

const poolData = {
  UserPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID as string,
  ClientId: import.meta.env.VITE_COGNITO_CLIENT_ID as string,
};

const userPool = new CognitoUserPool(poolData);

export interface AuthUser {
  username: string;
  email: string;
  workspaceId: string;
  idToken: string;
  accessToken: string;
}

function sessionToAuthUser(username: string, session: CognitoUserSession): AuthUser {
  const idToken = session.getIdToken();
  const payload = idToken.decodePayload();

  return {
    username,
    email: payload['email'] ?? username,
    workspaceId: payload['custom:workspace_id'] ?? payload['sub'] ?? '',
    idToken: idToken.getJwtToken(),
    accessToken: session.getAccessToken().getJwtToken(),
  };
}

/**
 * Sign in with username + password via Cognito SRP.
 * Returns an AuthUser on success.
 */
export function signIn(username: string, password: string): Promise<AuthUser> {
  return new Promise((resolve, reject) => {
    const authDetails = new AuthenticationDetails({ Username: username, Password: password });
    const cognitoUser = new CognitoUser({ Username: username, Pool: userPool });

    cognitoUser.authenticateUser(authDetails, {
      onSuccess(session) {
        resolve(sessionToAuthUser(username, session));
      },
      onFailure(err) {
        reject(err);
      },
      newPasswordRequired(_userAttributes, _requiredAttributes) {
        // Handle forced password change if needed
        reject(new Error('NEW_PASSWORD_REQUIRED'));
      },
    });
  });
}

/** Sign out current user locally and globally. */
export function signOut(): void {
  const user = userPool.getCurrentUser();
  if (user) user.signOut();
}

/**
 * Restore session from local storage (call on app boot).
 * Returns null if no valid session found.
 */
export function getCurrentSession(): Promise<AuthUser | null> {
  return new Promise((resolve) => {
    const user = userPool.getCurrentUser();
    if (!user) return resolve(null);

    user.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session || !session.isValid()) return resolve(null);
      resolve(sessionToAuthUser(user.getUsername(), session));
    });
  });
}

/**
 * Refresh and return the current access token (for API calls).
 * Returns null if user is not authenticated.
 */
export async function getAccessToken(): Promise<string | null> {
  const user = await getCurrentSession();
  return user?.idToken ?? null; // We use idToken as Bearer for Cognito custom:workspace_id
}
