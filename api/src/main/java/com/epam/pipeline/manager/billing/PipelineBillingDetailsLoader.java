/*
 * Copyright 2017-2020 EPAM Systems, Inc. (https://www.epam.com/)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.epam.pipeline.manager.billing;

import com.epam.pipeline.entity.billing.BillingGrouping;
import com.epam.pipeline.entity.pipeline.Pipeline;
import com.epam.pipeline.manager.pipeline.PipelineManager;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class PipelineBillingDetailsLoader implements EntityBillingDetailsLoader {

    @Value("${billing.empty.report.value:unknown}")
    private String emptyValue;

    @Autowired
    private final PipelineManager pipelineManager;

    @Override
    public BillingGrouping getGrouping() {
        return BillingGrouping.PIPELINE;
    }

    @Override
    public String loadName(final String entityIdentifier) {
        try {
            return pipelineManager.loadByNameOrId(entityIdentifier).getName();
        } catch (IllegalArgumentException e) {
            return entityIdentifier;
        }
    }

    @Override
    public Map<String, String> loadDetails(final String entityIdentifier) {
        final Map<String, String> details = new HashMap<>();
        final Pipeline pipeline = pipelineManager.loadByNameOrId(entityIdentifier);
        details.put(OWNER, pipeline.getOwner());
        return details;
    }

    @Override
    public Map<String, String> getEmptyDetails() {
        return Collections.singletonMap(OWNER, emptyValue);
    }
}
