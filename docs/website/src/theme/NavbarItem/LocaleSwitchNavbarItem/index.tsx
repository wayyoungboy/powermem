import React, {type MouseEventHandler, type ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {mergeSearchStrings, useHistorySelector} from '@docusaurus/theme-common';
import {useAlternatePageUtils} from '@docusaurus/theme-common/internal';
import styles from './styles.module.css';

type Props = {
  className?: string;
  mobile?: boolean;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
};

function GlobeIcon() {
  return (
    <svg
      aria-hidden="true"
      className={styles.icon}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M3.5 12h17M12 3c2.1 2.4 3.15 5.4 3.15 9S14.1 18.6 12 21c-2.1-2.4-3.15-5.4-3.15-9S9.9 5.4 12 3Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
    </svg>
  );
}

export default function LocaleSwitchNavbarItem({
  className,
  mobile = false,
  onClick,
}: Props): ReactNode {
  const {
    siteConfig,
    i18n: {currentLocale, localeConfigs},
  } = useDocusaurusContext();
  const alternatePageUtils = useAlternatePageUtils();
  const search = useHistorySelector((history) => history.location.search);
  const hash = useHistorySelector((history) => history.location.hash);
  const targetLocale = currentLocale === 'zh' ? 'en' : 'zh';
  const targetLabel = localeConfigs[targetLocale]?.label ?? targetLocale;
  const targetLocaleConfig = localeConfigs[targetLocale];
  const targetBaseUrl = targetLocaleConfig?.url === siteConfig.url
    ? `pathname://${alternatePageUtils.createUrl({
        locale: targetLocale,
        fullyQualified: false,
      })}`
    : alternatePageUtils.createUrl({
        locale: targetLocale,
        fullyQualified: true,
      });
  const targetPath = `${targetBaseUrl}${mergeSearchStrings([search], 'append')}${hash}`;

  const link = (
    <Link
      aria-label={`Switch language to ${targetLabel}`}
      className={clsx(
        mobile ? 'menu__link' : 'navbar__item navbar__link',
        styles.localeSwitch,
        className,
      )}
      title={`Switch language to ${targetLabel}`}
      to={targetPath}
      target="_self"
      autoAddBaseUrl={false}
      onClick={onClick}
    >
      <GlobeIcon />
    </Link>
  );

  if (mobile) {
    return <li className="menu__list-item">{link}</li>;
  }

  return link;
}
